#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 shavitmichael, OzzieIsaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import base64
import os
import uuid
from datetime import datetime
from time import gmtime, strftime
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from flask import (
    Blueprint,
    request,
    make_response,
    jsonify,
    current_app,
    url_for,
    redirect,
    abort
)
from flask_login import login_required
from werkzeug.datastructures import Headers
from sqlalchemy import func
import requests

from . import config, logger, kobo_auth, db, helper
from .services import SyncToken as SyncToken
from .web import download_required
from .kobo_auth import requires_kobo_auth

KOBO_FORMATS = {"KEPUB": ["KEPUB"], "EPUB": ["EPUB3", "EPUB"]}
KOBO_STOREAPI_URL = "https://storeapi.kobo.com"

kobo = Blueprint("kobo", __name__, url_prefix="/kobo/<auth_token>")
kobo_auth.disable_failed_auth_redirect_for_blueprint(kobo)
kobo_auth.register_url_value_preprocessor(kobo)

log = logger.create()

def get_store_url_for_current_request():
    # Programmatically modify the current url to point to the official Kobo store
    base, sep, request_path_with_auth_token = request.full_path.rpartition("/kobo/")
    auth_token, sep, request_path = request_path_with_auth_token.rstrip("?").partition(
        "/"
    )
    return KOBO_STOREAPI_URL + "/" + request_path


CONNECTION_SPECIFIC_HEADERS = [
    "connection",
    "content-encoding",
    "content-length",
    "transfer-encoding",
]

def get_kobo_activated():
    return config.config_kobo_sync


def make_request_to_kobo_store(sync_token=None):
    outgoing_headers = Headers(request.headers)
    outgoing_headers.remove("Host")
    if sync_token:
        sync_token.set_kobo_store_header(outgoing_headers)

    store_response = requests.request(
        method=request.method,
        url=get_store_url_for_current_request(),
        headers=outgoing_headers,
        data=request.get_data(),
        allow_redirects=False,
        timeout=(2, 10)
    )
    return store_response


def redirect_or_proxy_request():
    if config.config_kobo_proxy:
        if request.method == "GET":
            return redirect(get_store_url_for_current_request(), 307)
        if request.method == "DELETE":
            log.info('Delete Book')
            return make_response(jsonify({}))
        else:
            # The Kobo device turns other request types into GET requests on redirects, so we instead proxy to the Kobo store ourselves.
            store_response = make_request_to_kobo_store()

            response_headers = store_response.headers
            for header_key in CONNECTION_SPECIFIC_HEADERS:
                response_headers.pop(header_key, default=None)

            return make_response(
                store_response.content, store_response.status_code, response_headers.items()
            )
    else:
        return make_response(jsonify({}))


@kobo.route("/v1/library/sync")
@requires_kobo_auth
@download_required
def HandleSyncRequest():
    sync_token = SyncToken.SyncToken.from_headers(request.headers)
    log.info("Kobo library sync request received.")
    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to server port')

    # TODO: Limit the number of books return per sync call, and rely on the sync-continuatation header
    # instead so that the device triggers another sync.

    new_books_last_modified = sync_token.books_last_modified
    new_books_last_created = sync_token.books_last_created
    entitlements = []

    # We reload the book database so that the user get's a fresh view of the library
    # in case of external changes (e.g: adding a book through Calibre).
    db.reconnect_db(config)

    # sqlite gives unexpected results when performing the last_modified comparison without the datetime cast.
    # It looks like it's treating the db.Books.last_modified field as a string and may fail
    # the comparison because of the +00:00 suffix.
    changed_entries = (
        db.session.query(db.Books)
        .join(db.Data)
        .filter(func.datetime(db.Books.last_modified) > sync_token.books_last_modified)
        .filter(db.Data.format.in_(KOBO_FORMATS))
        .all()
    )

    for book in changed_entries:
        entitlement = {
            "BookEntitlement": create_book_entitlement(book),
            "BookMetadata": get_metadata(book),
            "ReadingState": reading_state(book),
        }
        if book.timestamp > sync_token.books_last_created:
            entitlements.append({"NewEntitlement": entitlement})
        else:
            entitlements.append({"ChangedEntitlement": entitlement})

        new_books_last_modified = max(
            book.last_modified, sync_token.books_last_modified
        )
        new_books_last_created = max(book.timestamp, sync_token.books_last_created)

    sync_token.books_last_created = new_books_last_created
    sync_token.books_last_modified = new_books_last_modified

    if config.config_kobo_proxy:
        return generate_sync_response(request, sync_token, entitlements)

    return make_response(jsonify(entitlements))
    # Missing feature: Detect server-side book deletions.


def generate_sync_response(request, sync_token, entitlements):
    extra_headers = {}
    if config.config_kobo_proxy:
        # Merge in sync results from the official Kobo store.
        try:
            store_response = make_request_to_kobo_store(sync_token)

            store_entitlements = store_response.json()
            entitlements += store_entitlements
            sync_token.merge_from_store_response(store_response)
            extra_headers["x-kobo-sync"] = store_response.headers.get("x-kobo-sync")
            extra_headers["x-kobo-sync-mode"] = store_response.headers.get("x-kobo-sync-mode")
            extra_headers["x-kobo-recent-reads"] = store_response.headers.get("x-kobo-recent-reads")

        except Exception as e:
            log.error("Failed to receive or parse response from Kobo's sync endpoint: " + str(e))
    sync_token.to_headers(extra_headers)

    response = make_response(jsonify(entitlements), extra_headers)

    return response


@kobo.route("/v1/library/<book_uuid>/metadata")
@requires_kobo_auth
@download_required
def HandleMetadataRequest(book_uuid):
    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to server port')
    log.info("Kobo library metadata request received for book %s" % book_uuid)
    book = db.session.query(db.Books).filter(db.Books.uuid == book_uuid).first()
    if not book or not book.data:
        log.info(u"Book %s not found in database", book_uuid)
        return redirect_or_proxy_request()

    metadata = get_metadata(book)
    return jsonify([metadata])


def get_download_url_for_book(book, book_format):
    if not current_app.wsgi_app.is_proxied:
        if ':' in request.host and not request.host.endswith(']') :
            host = "".join(request.host.split(':')[:-1])
        else:
            host = request.host
        return "{url_scheme}://{url_base}:{url_port}/download/{book_id}/{book_format}".format(
            url_scheme=request.scheme,
            url_base=host,
            url_port=config.config_port,
            book_id=book.id,
            book_format=book_format.lower()
        )
    return url_for(
        "web.download_link",
        book_id=book.id,
        book_format=book_format.lower(),
        _external=True,
    )


def create_book_entitlement(book):
    book_uuid = book.uuid
    return {
        "Accessibility": "Full",
        "ActivePeriod": {"From": current_time(),},
        "Created": book.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "CrossRevisionId": book_uuid,
        "Id": book_uuid,
        "IsHiddenFromArchive": False,
        "IsLocked": False,
        # Setting this to true removes from the device.
        "IsRemoved": False,
        "LastModified": book.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "OriginCategory": "Imported",
        "RevisionId": book_uuid,
        "Status": "Active",
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


def get_metadata(book):
    download_urls = []
    for book_data in book.data:
        if book_data.format not in KOBO_FORMATS:
            continue
        for kobo_format in KOBO_FORMATS[book_data.format]:
            # log.debug('Id: %s, Format: %s' % (book.id, kobo_format))
            download_urls.append(
                {
                    "Format": kobo_format,
                    "Size": book_data.uncompressed_size,
                    "Url": get_download_url_for_book(book, book_data.format),
                    # The Kobo forma accepts platforms: (Generic, Android)
                    "Platform": "Generic",
                    # "DrmType": "None", # Not required
                }
            )

    book_uuid = book.uuid
    metadata = {
        "Categories": ["00000000-0000-0000-0000-000000000001",],
        "Contributors": get_author(book),
        "CoverImageId": book_uuid,
        "CrossRevisionId": book_uuid,
        "CurrentDisplayPrice": {"CurrencyCode": "USD", "TotalAmount": 0},
        "CurrentLoveDisplayPrice": {"TotalAmount": 0},
        "Description": get_description(book),
        "DownloadUrls": download_urls,
        "EntitlementId": book_uuid,
        "ExternalIds": [],
        "Genre": "00000000-0000-0000-0000-000000000001",
        "IsEligibleForKoboLove": False,
        "IsInternetArchive": False,
        "IsPreOrder": False,
        "IsSocialEnabled": True,
        "Language": "en",
        "PhoneticPronunciations": {},
        "PublicationDate": book.pubdate,
        "Publisher": {"Imprint": "", "Name": get_publisher(book),},
        "RevisionId": book_uuid,
        "Title": book.title,
        "WorkId": book_uuid,
    }

    if get_series(book):
        if sys.version_info < (3, 0):
            name = get_series(book).encode("utf-8")
        else:
            name = get_series(book)
        metadata["Series"] = {
            "Name": get_series(book),
            "Number": book.series_index,
            "NumberFloat": float(book.series_index),
            # Get a deterministic id based on the series name.
            "Id": uuid.uuid3(uuid.NAMESPACE_DNS, name),
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


@kobo.route("/<book_uuid>/image.jpg")
@requires_kobo_auth
def HandleCoverImageRequest(book_uuid):
    book_cover = helper.get_book_cover_with_uuid(
        book_uuid, use_generic_cover_on_failure=False
    )
    if not book_cover:
        if config.config_kobo_proxy:
            log.debug("Cover for unknown book: %s proxied to kobo" % book_uuid)
            return redirect(get_store_url_for_current_request(), 307)
        else:
            log.debug("Cover for unknown book: %s requested" % book_uuid)
            return redirect_or_proxy_request()
    log.debug("Cover request received for book %s" % book_uuid)
    return book_cover


@kobo.route("")
def TopLevelEndpoint():
    return make_response(jsonify({}))


# TODO: Implement the following routes
@kobo.route("/v1/library/<dummy>", methods=["DELETE", "GET"])
@kobo.route("/v1/library/<book_uuid>/state", methods=["PUT"])
@kobo.route("/v1/library/tags", methods=["POST"])
@kobo.route("/v1/library/tags/<shelf_name>", methods=["POST"])
@kobo.route("/v1/library/tags/<tag_id>", methods=["DELETE"])
def HandleUnimplementedRequest(dummy=None, book_uuid=None, shelf_name=None, tag_id=None):
    log.debug("Unimplemented Library Request received: %s", request.base_url)
    return redirect_or_proxy_request()


# TODO: Implement the following routes
@kobo.route("/v1/user/loyalty/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/user/profile", methods=["GET", "POST"])
@kobo.route("/v1/user/wishlist", methods=["GET", "POST"])
@kobo.route("/v1/user/recommendations", methods=["GET", "POST"])
@kobo.route("/v1/analytics/<dummy>", methods=["GET", "POST"])
def HandleUserRequest(dummy=None):
    log.debug("Unimplemented User Request received: %s", request.base_url)
    return redirect_or_proxy_request()


@kobo.route("/v1/products/<dummy>/prices", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/recommendations", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/nextread", methods=["GET", "POST"])
@kobo.route("/v1/products/<dummy>/reviews", methods=["GET", "POST"])
@kobo.route("/v1/products/books/<dummy>", methods=["GET", "POST"])
@kobo.route("/v1/products/dailydeal", methods=["GET", "POST"])
@kobo.route("/v1/products", methods=["GET", "POST"])
def HandleProductsRequest(dummy=None):
    log.debug("Unimplemented Products Request received: %s", request.base_url)
    return redirect_or_proxy_request()


@kobo.app_errorhandler(404)
def handle_404(err):
    # This handler acts as a catch-all for endpoints that we don't have an interest in
    # implementing (e.g: v1/analytics/gettests, v1/user/recommendations, etc)
    log.debug("Unknown Request received: %s", request.base_url)
    return redirect_or_proxy_request()


def make_calibre_web_auth_response():
    # As described in kobo_auth.py, CalibreWeb doesn't make use practical use of this auth/device API call for
    # authentation (nor for authorization). We return a dummy response just to keep the device happy.
    content = request.get_json()
    AccessToken = base64.b64encode(os.urandom(24)).decode('utf-8')
    RefreshToken = base64.b64encode(os.urandom(24)).decode('utf-8')
    return  make_response(
        jsonify(
            {
                "AccessToken": AccessToken,
                "RefreshToken": RefreshToken,
                "TokenType": "Bearer",
                "TrackingId": str(uuid.uuid4()),
                "UserKey": content['UserKey'],
            }
        )
    )


@kobo.route("/v1/auth/device", methods=["POST"])
@requires_kobo_auth
def HandleAuthRequest():
    log.debug('Kobo Auth request')
    if config.config_kobo_proxy:
        try:
            return redirect_or_proxy_request()
        except:
            log.error("Failed to receive or parse response from Kobo's auth endpoint. Falling back to un-proxied mode.")
    return make_calibre_web_auth_response()


def make_calibre_web_init_response(calibre_web_url):
        resources = NATIVE_KOBO_RESOURCES(calibre_web_url)
        response = make_response(jsonify({"Resources": resources}))
        response.headers["x-kobo-apitoken"] = "e30="
        return response


@kobo.route("/v1/initialization")
@requires_kobo_auth
def HandleInitRequest():
    log.info('Init')

    if not current_app.wsgi_app.is_proxied:
        log.debug('Kobo: Received unproxied request, changed request port to server port')
        if ':' in request.host and not request.host.endswith(']'):
            host = "".join(request.host.split(':')[:-1])
        else:
            host = request.host
        calibre_web_url = "{url_scheme}://{url_base}:{url_port}".format(
            url_scheme=request.scheme,
            url_base=host,
            url_port=config.config_port
        )
    else:
        calibre_web_url = url_for("web.index", _external=True).strip("/")

    if config.config_kobo_proxy:
        try:
            store_response = make_request_to_kobo_store()

            store_response_json = store_response.json()
            if "Resources" in store_response_json:
                kobo_resources = store_response_json["Resources"]
                # calibre_web_url = url_for("web.index", _external=True).strip("/")
                kobo_resources["image_host"] = calibre_web_url
                kobo_resources["image_url_quality_template"] = unquote(calibre_web_url + url_for("kobo.HandleCoverImageRequest",
                    auth_token = kobo_auth.get_auth_token(),
                    book_uuid="{ImageId}"))
                kobo_resources["image_url_template"] = unquote(calibre_web_url + url_for("kobo.HandleCoverImageRequest",
                    auth_token = kobo_auth.get_auth_token(),
                    book_uuid="{ImageId}"))

            return make_response(store_response_json, store_response.status_code)
        except:
            log.error("Failed to receive or parse response from Kobo's init endpoint. Falling back to un-proxied mode.")

    return make_calibre_web_init_response(calibre_web_url)


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
        "image_url_quality_template": unquote(calibre_web_url + url_for("kobo.HandleCoverImageRequest",
                auth_token = kobo_auth.get_auth_token(),
                book_uuid="{ImageId}")),
        "image_url_template":  unquote(calibre_web_url + url_for("kobo.HandleCoverImageRequest",
                auth_token = kobo_auth.get_auth_token(),
                book_uuid="{ImageId}")),
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
