#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import uuid
import os
from datetime import datetime, tzinfo, timedelta
from time import gmtime, strftime

from b2sdk.account_info.in_memory import InMemoryAccountInfo
from b2sdk.api import B2Api
from jsonschema import validate, exceptions
from flask import Blueprint, request, make_response, jsonify, json, send_file
from flask_login import login_required
from sqlalchemy import func

from . import config, logger, kobo_auth, ub, db, helper
from .constants import CONFIG_DIR as _CONFIG_DIR
from .web import download_required

B2_SECRETS = os.path.join(_CONFIG_DIR, "b2_secrets.json")

kobo = Blueprint("kobo", __name__)
kobo_auth.disable_failed_auth_redirect_for_blueprint(kobo)

log = logger.create()

import base64


def b64encode(data):
    return base64.b64encode(data)


def b64encode_json(json_data):
    return b64encode(json.dumps(json_data))


# Python3 has a timestamp() method we could be calling, however it's not avaiable in python2.
def to_epoch_timestamp(datetime_object):
    return (datetime_object - datetime(1970, 1, 1)).total_seconds()


class SyncToken:
    """ The SyncToken is used to persist state accross requests.
    When serialized over the response headers, the Kobo device will propagate the token onto following requests to the service.
    As an example use-case, the SyncToken is used to detect books that have been added to the library since the last time the device synced to the server.

    Attributes:
        books_last_created: Datetime representing the newest book that the device knows about.
        books_last_modified: Datetime representing the last modified book that the device knows about.
    """

    SYNC_TOKEN_HEADER = "x-kobo-synctoken"
    VERSION = "1-0-0"
    MIN_VERSION = "1-0-0"

    token_schema = {
        "type": "object",
        "properties": {"version": {"type": "string"}, "data": {"type": "object"},},
    }
    # This Schema doesn't contain enough information to detect and propagate book deletions from Calibre to the device.
    # A potential solution might be to keep a list of all known book uuids in the token, and look for any missing from the db.
    data_schema_v1 = {
        "type": "object",
        "properties": {
            "raw_kobo_store_token": {"type": "string"},
            "books_last_modified": {"type": "string"},
            "books_last_created": {"type": "string"},
        },
    }

    def __init__(
        self,
        raw_kobo_store_token="",
        books_last_created=datetime.min,
        books_last_modified=datetime.min,
    ):
        self.raw_kobo_store_token = raw_kobo_store_token
        self.books_last_created = books_last_created
        self.books_last_modified = books_last_modified

    @staticmethod
    def from_headers(headers):
        sync_token_header = headers.get(SyncToken.SYNC_TOKEN_HEADER, "")
        if sync_token_header == "":
            return SyncToken()

        # On the first sync from a Kobo device, we may receive the SyncToken
        # from the official Kobo store. Without digging too deep into it, that
        # token is of the form [b64encoded blob].[b64encoded blob 2]
        if "." in sync_token_header:
            return SyncToken(raw_kobo_store_token=sync_token_header)

        sync_token_json = json.loads(
            base64.b64decode(sync_token_header + "=" * (-len(sync_token_header) % 4))
        )
        try:
            validate(sync_token_json, SyncToken.token_schema)
            if sync_token_json["version"] < SyncToken.MIN_VERSION:
                raise ValueError

            data_json = sync_token_json["data"]
            validate(sync_token_json, SyncToken.data_schema_v1)
        except (exceptions.ValidationError, ValueError) as e:
            log.error("Sync token contents do not follow the expected json schema.")
            return SyncToken()

        raw_kobo_store_token = data_json["raw_kobo_store_token"]
        try:
            books_last_modified = datetime.utcfromtimestamp(
                data_json["books_last_modified"]
            )
            books_last_created = datetime.utcfromtimestamp(
                data_json["books_last_created"]
            )
        except TypeError:
            log.error("SyncToken timestamps don't parse to a datetime.")
            return SyncToken(raw_kobo_store_token=raw_kobo_store_token)

        return SyncToken(
            raw_kobo_store_token=raw_kobo_store_token,
            books_last_created=books_last_created,
            books_last_modified=books_last_modified,
        )

    def to_headers(self, headers):
        headers[SyncToken.SYNC_TOKEN_HEADER] = self.build_sync_token()

    def build_sync_token(self):
        token = {
            "version": SyncToken.VERSION,
            "data": {
                "raw_kobo_store_token": self.raw_kobo_store_token,
                "books_last_modified": to_epoch_timestamp(self.books_last_modified),
                "books_last_created": to_epoch_timestamp(self.books_last_created),
            },
        }
        return b64encode_json(token)


@kobo.route("/v1/library/sync")
@login_required
@download_required
def HandleSyncRequest():
    sync_token = SyncToken.from_headers(request.headers)
    log.info("Kobo library sync request received.")

    # TODO: Limit the number of books return per sync call, and rely on the sync-continuatation header
    # instead so that the device triggers another sync.

    new_books_last_modified = sync_token.books_last_modified
    new_books_last_created = sync_token.books_last_created
    entitlements = []

    # sqlite gives unexpected results when performing the last_modified comparison without the datetime cast.
    # It looks like it's treating the db.Books.last_modified field as a string and may fail
    # the comparison because of the +00:00 suffix.
    changed_entries = (
        db.session.query(db.Books)
        .filter(func.datetime(db.Books.last_modified) > sync_token.books_last_modified)
        .all()
    )
    for book in changed_entries:
        entitlement = CreateEntitlement(book)
        if book.timestamp > sync_token.books_last_created:
            entitlements.append({"NewEntitlement": entitlement})
        else:
            entitlements.append({"ChangedEntitlement": entitlement})

        new_books_last_modified = max(
            book.last_modified, sync_token.books_last_modified
        )
        new_books_last_created = max(book.timestamp, sync_token.books_last_modified)

    sync_token.books_last_created = new_books_last_created
    sync_token.books_last_modified = new_books_last_modified

    # Missing feature: Detect server-side book deletions.

    # Missing feature: Join the response with results from the official Kobo store so that users can still buy and access books from the device store (particularly while on-the-road).

    response = make_response(jsonify(entitlements))

    sync_token.to_headers(response.headers)
    response.headers["x-kobo-sync-mode"] = "delta"
    response.headers["x-kobo-apitoken"] = "e30="
    return response


@kobo.route("/v1/library/<book_uuid>/metadata")
@login_required
@download_required
def get_metadata__v1(book_uuid):
    log.info("Kobo library metadata request received for book %s" % book_uuid)
    book = db.session.query(db.Books).filter(db.Books.uuid == book_uuid).first()
    if not book:
        log.info(u"Book %s not found in database", book_uuid)
        return make_response("Book not found in database.", 404)

    download_url = get_download_url_for_book(book)
    if not download_url:
        return make_response("Could not get a download url for book.", 500)

    metadata = create_metadata(book)
    metadata["DownloadUrls"] = [
        {
            "DrmType": "SignedNoDrm",
            "Format": "KEPUB",
            "Platform": "Android",
            # TODO: Set the file size.
            # "Size": file_info["contentLength"],
            "Url": download_url,
        }
    ]
    return jsonify([metadata])


def get_download_url_for_book(book):
    return "{url_base}/download/{book_id}/kepub".format(
        url_base=config.config_server_url, book_id=book.id
    )


def get_download_url_for_book_b2(book):
    # TODO: Research what formats Kobo will support over the sync protocol.
    # For now let's just assume all books are converted to KEPUB.
    data = (
        db.session.query(db.Data)
        .filter(db.Data.book == book.id)
        .filter(db.Data.format == "KEPUB")
        .first()
    )

    if not data:
        log.info(u"Book %s does have a kepub format", book_uuid)
        return None

    file_name = data.name + ".kepub"
    file_path = os.path.join(book.path, file_name)

    if not os.path.isfile(B2_SECRETS):
        log.error(u"b2 secret file not found")
        return None
    with open(B2_SECRETS, "r") as filedata:
        secrets = json.load(filedata)

    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account(
        "production", secrets["application_key_id"], secrets["application_key"]
    )
    bucket = b2_api.get_bucket_by_name(secrets["bucket_name"])
    if not bucket:
        log.error(u"b2 bucket not found")
        return None

    download_url = b2_api.get_download_url_for_file_name(
        secrets["bucket_name"], file_path
    )
    download_authorization = bucket.get_download_authorization(
        file_path, valid_duration_in_seconds=600
    )
    return download_url + "?Authorization=" + download_authorization


def CreateBookEntitlement(book):
    book_uuid = book.uuid
    return {
        "Accessibility": "Full",
        "ActivePeriod": {"From": current_time(),},
        "Created": book.timestamp,
        "CrossRevisionId": book_uuid,
        "Id": book_uuid,
        "IsHiddenFromArchive": False,
        "IsLocked": False,
        # Setting this to true removes from the device.
        "IsRemoved": False,
        "LastModified": book.last_modified,
        "OriginCategory": "Imported",
        "RevisionId": book_uuid,
        "Status": "Active",
    }


def CreateEntitlement(book):
    return {
        "BookEntitlement": CreateBookEntitlement(book),
        "BookMetadata": create_metadata(book),
        "ReadingState": reading_state(book),
    }


def current_time():
    return strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())


def get_description(book):
    if not book.comments:
        return None
    return book.comments[0].text


# TODO handle multiple authors
def get_author(book):
    if not book.authors:
        return None
    return book.authors[0].name


def get_publisher(book):
    if not book.publishers:
        return None
    return book.publishers[0].name


def get_series(book):
    if not book.series:
        return None
    return book.series[0].name


def create_metadata(book):
    book_uuid = book.uuid
    metadata = {
        "Categories": ["00000000-0000-0000-0000-000000000001",],
        "Contributors": get_author(book),
        "CoverImageId": book_uuid,
        "CrossRevisionId": book_uuid,
        "CurrentDisplayPrice": {"CurrencyCode": "USD", "TotalAmount": 0},
        "CurrentLoveDisplayPrice": {"TotalAmount": 0},
        "Description": get_description(book),
        "DownloadUrls": [
            # Looks like we need to pass at least one url in the
            # v1/library/sync call. The new entitlement is ignored
            # otherwise.
            # May want to experiment more with this.
            {
                "DrmType": "None",
                "Format": "KEPUB",
                "Platform": "Android",
                "Size": 1024775,
                "Url": "https://google.com",
            },
        ],
        "EntitlementId": book_uuid,
        "ExternalIds": [],
        "Genre": "00000000-0000-0000-0000-000000000001",
        "IsEligibleForKoboLove": False,
        "IsInternetArchive": False,
        "IsPreOrder": False,
        "IsSocialEnabled": True,
        "Language": "en",
        "PhoneticPronunciations": {},
        "PublicationDate": "2019-02-03T00:25:03.0000000Z",  # current_time(),
        "Publisher": {"Imprint": "", "Name": get_publisher(book),},
        "RevisionId": book_uuid,
        "Title": book.title,
        "WorkId": book_uuid,
    }

    if get_series(book):
        metadata["Series"] = {
            "Name": get_series(book),
            "Number": book.series_index,
            "NumberFloat": float(book.series_index),
            # Get a deterministic id based on the series name.
            "Id": uuid.uuid3(uuid.NAMESPACE_DNS, get_series(book).encode("utf-8")),
        }

    return metadata


def reading_state(book):
    # TODO: Implement
    reading_state = {
        # "StatusInfo": {
        #     "LastModified": get_single_cc_value(book, "lastreadtimestamp"),
        #     "Status": get_single_cc_value(book, "reading_status"),
        # }
        # TODO: CurrentBookmark, Location
    }
    return reading_state


@kobo.route(
    "/<book_uuid>/<horizontal>/<vertical>/<jpeg_quality>/<monochrome>/image.jpg"
)
def HandleCoverImageRequest(book_uuid, horizontal, vertical, jpeg_quality, monochrome):
    book_cover = helper.get_book_cover_with_uuid(
        book_uuid, use_generic_cover_on_failure=False
    )
    if not book_cover:
        return make_response()
    return book_cover


@kobo.route("/v1/user/profile")
@kobo.route("/v1/user/loyalty/benefits")
@kobo.route("/v1/analytics/gettests/", methods=["GET", "POST"])
@kobo.route("/v1/user/wishlist")
@kobo.route("/v1/user/<dummy>")
@kobo.route("/v1/user/recommendations")
@kobo.route("/v1/products/<dummy>")
@kobo.route("/v1/products/<dummy>/nextread")
@kobo.route("/v1/products/featured/<dummy>")
@kobo.route("/v1/products/featured/")
@kobo.route("/v1/library/<dummy>", methods=["DELETE", "GET"])  # TODO: implement
def HandleDummyRequest(dummy=None):
    return make_response(jsonify({}))


@kobo.route("/v1/auth/device", methods=["POST"])
def HandleAuthRequest():
    # This AuthRequest isn't used for most of our usecases.
    response = make_response(
        jsonify(
            {
                "AccessToken": "abcde",
                "RefreshToken": "abcde",
                "TokenType": "Bearer",
                "TrackingId": "abcde",
                "UserKey": "abcdefgeh",
            }
        )
    )
    return response


@kobo.route("/v1/initialization")
def HandleInitRequest():
    resources = NATIVE_KOBO_RESOURCES(calibre_web_url=config.config_server_url)
    response = make_response(jsonify({"Resources": resources}))
    response.headers["x-kobo-apitoken"] = "e30="
    return response


def NATIVE_KOBO_RESOURCES(calibre_web_url):
    return {
        "account_page": "https://secure.kobobooks.com/profile",
        "account_page_rakuten": "https://my.rakuten.co.jp/",
        "add_entitlement": "https://storeapi.kobo.com/v1/library/{RevisionIds}",
        "affiliaterequest": "https://storeapi.kobo.com/v1/affiliate",
        "audiobook_subscription_orange_deal_inclusion_url": "https://authorize.kobo.com/inclusion",
        "authorproduct_recommendations": "https://storeapi.kobo.com/v1/products/books/authors/recommendations",
        "autocomplete": "https://storeapi.kobo.com/v1/products/autocomplete",
        "blackstone_header": {"key": "x-amz-request-payer", "value": "requester"},
        "book": "https://storeapi.kobo.com/v1/products/books/{ProductId}",
        "book_detail_page": "https://store.kobobooks.com/{culture}/ebook/{slug}",
        "book_detail_page_rakuten": "http://books.rakuten.co.jp/rk/{crossrevisionid}",
        "book_landing_page": "https://store.kobobooks.com/ebooks",
        "book_subscription": "https://storeapi.kobo.com/v1/products/books/subscriptions",
        "categories": "https://storeapi.kobo.com/v1/categories",
        "categories_page": "https://store.kobobooks.com/ebooks/categories",
        "category": "https://storeapi.kobo.com/v1/categories/{CategoryId}",
        "category_featured_lists": "https://storeapi.kobo.com/v1/categories/{CategoryId}/featured",
        "category_products": "https://storeapi.kobo.com/v1/categories/{CategoryId}/products",
        "checkout_borrowed_book": "https://storeapi.kobo.com/v1/library/borrow",
        "configuration_data": "https://storeapi.kobo.com/v1/configuration",
        "content_access_book": "https://storeapi.kobo.com/v1/products/books/{ProductId}/access",
        "customer_care_live_chat": "https://v2.zopim.com/widget/livechat.html?key=Y6gwUmnu4OATxN3Tli4Av9bYN319BTdO",
        "daily_deal": "https://storeapi.kobo.com/v1/products/dailydeal",
        "deals": "https://storeapi.kobo.com/v1/deals",
        "delete_entitlement": "https://storeapi.kobo.com/v1/library/{Ids}",
        "delete_tag": "https://storeapi.kobo.com/v1/library/tags/{TagId}",
        "delete_tag_items": "https://storeapi.kobo.com/v1/library/tags/{TagId}/items/delete",
        "device_auth": "https://storeapi.kobo.com/v1/auth/device",
        "device_refresh": "https://storeapi.kobo.com/v1/auth/refresh",
        "dictionary_host": "https://kbdownload1-a.akamaihd.net",
        "discovery_host": "https://discovery.kobobooks.com",
        "eula_page": "https://www.kobo.com/termsofuse?style=onestore",
        "exchange_auth": "https://storeapi.kobo.com/v1/auth/exchange",
        "external_book": "https://storeapi.kobo.com/v1/products/books/external/{Ids}",
        "facebook_sso_page": "https://authorize.kobo.com/signin/provider/Facebook/login?returnUrl=http://store.kobobooks.com/",
        "featured_list": "https://storeapi.kobo.com/v1/products/featured/{FeaturedListId}",
        "featured_lists": "https://storeapi.kobo.com/v1/products/featured",
        "free_books_page": {
            "EN": "https://www.kobo.com/{region}/{language}/p/free-ebooks",
            "FR": "https://www.kobo.com/{region}/{language}/p/livres-gratuits",
            "IT": "https://www.kobo.com/{region}/{language}/p/libri-gratuiti",
            "NL": "https://www.kobo.com/{region}/{language}/List/bekijk-het-overzicht-van-gratis-ebooks/QpkkVWnUw8sxmgjSlCbJRg",
            "PT": "https://www.kobo.com/{region}/{language}/p/livros-gratis",
        },
        "fte_feedback": "https://storeapi.kobo.com/v1/products/ftefeedback",
        "get_tests_request": "https://storeapi.kobo.com/v1/analytics/gettests",
        "giftcard_epd_redeem_url": "https://www.kobo.com/{storefront}/{language}/redeem-ereader",
        "giftcard_redeem_url": "https://www.kobo.com/{storefront}/{language}/redeem",
        "help_page": "http://www.kobo.com/help",
        "image_host": calibre_web_url,
        "image_url_quality_template": calibre_web_url
        + "/{ImageId}/{Width}/{Height}/{Quality}/{IsGreyscale}/image.jpg",
        "image_url_template": calibre_web_url
        + "/{ImageId}/{Width}/{Height}/false/image.jpg",
        "kobo_audiobooks_enabled": "False",
        "kobo_audiobooks_orange_deal_enabled": "False",
        "kobo_audiobooks_subscriptions_enabled": "False",
        "kobo_nativeborrow_enabled": "True",
        "kobo_onestorelibrary_enabled": "False",
        "kobo_redeem_enabled": "True",
        "kobo_shelfie_enabled": "False",
        "kobo_subscriptions_enabled": "False",
        "kobo_superpoints_enabled": "False",
        "kobo_wishlist_enabled": "True",
        "library_book": "https://storeapi.kobo.com/v1/user/library/books/{LibraryItemId}",
        "library_items": "https://storeapi.kobo.com/v1/user/library",
        "library_metadata": "https://storeapi.kobo.com/v1/library/{Ids}/metadata",
        "library_prices": "https://storeapi.kobo.com/v1/user/library/previews/prices",
        "library_stack": "https://storeapi.kobo.com/v1/user/library/stacks/{LibraryItemId}",
        "library_sync": "https://storeapi.kobo.com/v1/library/sync",
        "love_dashboard_page": "https://store.kobobooks.com/{culture}/kobosuperpoints",
        "love_points_redemption_page": "https://store.kobobooks.com/{culture}/KoboSuperPointsRedemption?productId={ProductId}",
        "magazine_landing_page": "https://store.kobobooks.com/emagazines",
        "notifications_registration_issue": "https://storeapi.kobo.com/v1/notifications/registration",
        "oauth_host": "https://oauth.kobo.com",
        "overdrive_account": "https://auth.overdrive.com/account",
        "overdrive_library": "https://{libraryKey}.auth.overdrive.com/library",
        "overdrive_library_finder_host": "https://libraryfinder.api.overdrive.com",
        "overdrive_thunder_host": "https://thunder.api.overdrive.com",
        "password_retrieval_page": "https://www.kobobooks.com/passwordretrieval.html",
        "post_analytics_event": "https://storeapi.kobo.com/v1/analytics/event",
        "privacy_page": "https://www.kobo.com/privacypolicy?style=onestore",
        "product_nextread": "https://storeapi.kobo.com/v1/products/{ProductIds}/nextread",
        "product_prices": "https://storeapi.kobo.com/v1/products/{ProductIds}/prices",
        "product_recommendations": "https://storeapi.kobo.com/v1/products/{ProductId}/recommendations",
        "product_reviews": "https://storeapi.kobo.com/v1/products/{ProductIds}/reviews",
        "products": "https://storeapi.kobo.com/v1/products",
        "provider_external_sign_in_page": "https://authorize.kobo.com/ExternalSignIn/{providerName}?returnUrl=http://store.kobobooks.com/",
        "purchase_buy": "https://www.kobo.com/checkout/createpurchase/",
        "purchase_buy_templated": "https://www.kobo.com/{culture}/checkout/createpurchase/{ProductId}",
        "quickbuy_checkout": "https://storeapi.kobo.com/v1/store/quickbuy/{PurchaseId}/checkout",
        "quickbuy_create": "https://storeapi.kobo.com/v1/store/quickbuy/purchase",
        "rating": "https://storeapi.kobo.com/v1/products/{ProductId}/rating/{Rating}",
        "reading_state": "https://storeapi.kobo.com/v1/library/{Ids}/state",
        "redeem_interstitial_page": "https://store.kobobooks.com",
        "registration_page": "https://authorize.kobo.com/signup?returnUrl=http://store.kobobooks.com/",
        "related_items": "https://storeapi.kobo.com/v1/products/{Id}/related",
        "remaining_book_series": "https://storeapi.kobo.com/v1/products/books/series/{SeriesId}",
        "rename_tag": "https://storeapi.kobo.com/v1/library/tags/{TagId}",
        "review": "https://storeapi.kobo.com/v1/products/reviews/{ReviewId}",
        "review_sentiment": "https://storeapi.kobo.com/v1/products/reviews/{ReviewId}/sentiment/{Sentiment}",
        "shelfie_recommendations": "https://storeapi.kobo.com/v1/user/recommendations/shelfie",
        "sign_in_page": "https://authorize.kobo.com/signin?returnUrl=http://store.kobobooks.com/",
        "social_authorization_host": "https://social.kobobooks.com:8443",
        "social_host": "https://social.kobobooks.com",
        "stacks_host_productId": "https://store.kobobooks.com/collections/byproductid/",
        "store_home": "www.kobo.com/{region}/{language}",
        "store_host": "store.kobobooks.com",
        "store_newreleases": "https://store.kobobooks.com/{culture}/List/new-releases/961XUjtsU0qxkFItWOutGA",
        "store_search": "https://store.kobobooks.com/{culture}/Search?Query={query}",
        "store_top50": "https://store.kobobooks.com/{culture}/ebooks/Top",
        "tag_items": "https://storeapi.kobo.com/v1/library/tags/{TagId}/Items",
        "tags": "https://storeapi.kobo.com/v1/library/tags",
        "taste_profile": "https://storeapi.kobo.com/v1/products/tasteprofile",
        "update_accessibility_to_preview": "https://storeapi.kobo.com/v1/library/{EntitlementIds}/preview",
        "use_one_store": "False",
        "user_loyalty_benefits": "https://storeapi.kobo.com/v1/user/loyalty/benefits",
        "user_platform": "https://storeapi.kobo.com/v1/user/platform",
        "user_profile": "https://storeapi.kobo.com/v1/user/profile",
        "user_ratings": "https://storeapi.kobo.com/v1/user/ratings",
        "user_recommendations": "https://storeapi.kobo.com/v1/user/recommendations",
        "user_reviews": "https://storeapi.kobo.com/v1/user/reviews",
        "user_wishlist": "https://storeapi.kobo.com/v1/user/wishlist",
        "userguide_host": "https://kbdownload1-a.akamaihd.net",
        "wishlist_page": "https://store.kobobooks.com/{region}/{language}/account/wishlist",
    }
