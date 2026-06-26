from flask import Blueprint, jsonify, request
from flask_wtf.csrf import generate_csrf
from .cw_login import current_user
from .cw_babel import get_locale
from . import config, constants, calibre_db, ub, db, kobo_sync_status, helper
from .usermanagement import login_required_if_no_ano
from .editbooks import (
    edit_required, handle_title_on_edit, handle_author_on_edit, edit_book_ratings,
    edit_book_series_index, edit_book_comments, edit_book_tags,
    edit_book_series, edit_book_publisher, edit_book_languages,
    edit_all_cc_data, identifier_list, modify_identifiers
)
from datetime import datetime, timezone

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1.route('/book/<int:book_id>', methods=['GET'])
@login_required_if_no_ano
def get_book_detail(book_id):
    book = calibre_db.get_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
        
    is_archived = False
    read_status = False
    if current_user.is_authenticated and not current_user.is_anonymous:
        read_val = ub.session.query(ub.ReadBook).filter(
            ub.ReadBook.user_id == current_user.id,
            ub.ReadBook.book_id == book_id
        ).first()
        if read_val:
            read_status = read_val.read_status == ub.ReadBook.STATUS_FINISHED
            
        archived_val = ub.session.query(ub.ArchivedBook).filter(
            ub.ArchivedBook.user_id == current_user.id,
            ub.ArchivedBook.book_id == book_id
        ).first()
        if archived_val:
            is_archived = archived_val.is_archived
            
    comments_text = ""
    if book.comments and len(book.comments) > 0:
        comments_text = book.comments[0].text

    formats = []
    for data in book.data:
        formats.append({
            "id": data.id,
            "format": data.format,
            "size": data.uncompressed_size,
            "name": data.name
        })

    identifiers = []
    for identifier in book.identifiers:
        identifiers.append({
            "type": identifier.type,
            "val": identifier.val
        })

    authors_list = [author.name for author in book.authors]
    tags_list = [tag.name for tag in book.tags]
    series_name = book.series[0].name if book.series else None
    publisher_name = book.publishers[0].name if book.publishers else None
    
    book_shelves = []
    if current_user.is_authenticated and not current_user.is_anonymous:
        shelves_containing = ub.session.query(ub.BookShelf.shelf).filter(ub.BookShelf.book_id == book_id).all()
        book_shelves = [s[0] for s in shelves_containing]

    custom_columns = []
    try:
        cc = calibre_db.session.query(db.CustomColumns).filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).all()
        for c in cc:
            cc_string = "custom_column_" + str(c.id)
            val = getattr(book, cc_string, None)
            cc_val = None
            if val:
                if not c.is_multiple:
                    if len(val) > 0:
                        cc_val = val[0].value
                else:
                    cc_val = ",".join([str(v.value) for v in val])
            
            custom_columns.append({
                "id": c.id,
                "label": c.label,
                "name": c.name,
                "datatype": c.datatype,
                "is_multiple": bool(c.is_multiple),
                "value": cc_val
            })
    except Exception as e:
        pass

    return jsonify({
        "id": book.id,
        "title": book.title,
        "sort": book.sort,
        "author_sort": book.author_sort,
        "timestamp": book.timestamp.strftime("%Y-%m-%d %H:%M:%S") if book.timestamp else None,
        "pubdate": book.pubdate.strftime("%Y-%m-%d %H:%M:%S") if book.pubdate else None,
        "series_index": book.series_index,
        "last_modified": book.last_modified.strftime("%Y-%m-%d %H:%M:%S") if book.last_modified else None,
        "path": book.path,
        "has_cover": bool(book.has_cover),
        "uuid": book.uuid,
        "authors": " & ".join(authors_list),
        "authors_list": authors_list,
        "tags": ",".join(tags_list),
        "tags_list": tags_list,
        "series": series_name,
        "publisher": publisher_name,
        "comments": comments_text,
        "formats": formats,
        "identifiers": identifiers,
        "is_archived": is_archived,
        "read_status": read_status,
        "shelves": book_shelves,
        "custom_columns": custom_columns
    })

@api_v1.route('/book/<int:book_id>', methods=['PATCH', 'PUT'])
@login_required_if_no_ano
@edit_required
def patch_book(book_id):
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    if not book:
        return jsonify({"error": "Book not found"}), 404
        
    data = request.get_json() or {}
    to_save = {}
    modify_date = False
    
    if 'title' in data:
        to_save['title'] = data['title']
        modify_date |= handle_title_on_edit(book, data['title'])
        
    if 'authors' in data:
        authors_val = data['authors']
        if isinstance(authors_val, list):
            authors_str = " & ".join(authors_val)
        else:
            authors_str = authors_val
        to_save['authors'] = authors_str
        input_authors, author_change = handle_author_on_edit(book, authors_str)
        if author_change or ('title' in data and to_save.get('title') != book.title):
            modify_date = True
            helper.update_dir_structure(book.id, config.get_book_path(), input_authors[0])
            
    if 'rating' in data:
        to_save['rating'] = str(data['rating'])
        modify_date |= edit_book_ratings(to_save, book)
        
    if 'series_index' in data:
        to_save['series_index'] = str(data['series_index'])
        modify_date |= edit_book_series_index(to_save['series_index'], book)
        
    if 'comments' in data:
        to_save['comments'] = data['comments']
        modify_date |= edit_book_comments(data['comments'], book)
        
    if 'tags' in data:
        tags_val = data['tags']
        if isinstance(tags_val, list):
            tags_str = ",".join(tags_val)
        else:
            tags_str = tags_val
        to_save['tags'] = tags_str
        modify_date |= edit_book_tags(tags_str, book)
        
    if 'series' in data:
        to_save['series'] = data['series']
        modify_date |= edit_book_series(data['series'], book)
        
    if 'publisher' in data:
        to_save['publisher'] = data['publisher']
        modify_date |= edit_book_publisher(data['publisher'], book)
        
    if 'languages' in data:
        langs_val = data['languages']
        if isinstance(langs_val, list):
            langs_str = ",".join(langs_val)
        else:
            langs_str = langs_val
        to_save['languages'] = langs_str
        modify_date |= edit_book_languages(langs_str, book)

    if 'identifiers' in data:
        ident_dict = {}
        for idx, ident in enumerate(data['identifiers']):
            ident_dict[f'identifier-type-{idx}'] = ident['type']
            ident_dict[f'identifier-val-{idx}'] = ident['val']
        
        input_identifiers = identifier_list(ident_dict, book)
        modification, warning = modify_identifiers(input_identifiers, book.identifiers, calibre_db.session)
        modify_date |= modification

    if 'custom_columns' in data:
        cc_to_save = {}
        if isinstance(data['custom_columns'], list):
            for col in data['custom_columns']:
                cc_to_save[f"custom_column_{col['id']}"] = str(col['value']) if col['value'] is not None else ""
        elif isinstance(data['custom_columns'], dict):
            for k, v in data['custom_columns'].items():
                cc_to_save[k] = str(v) if v is not None else ""
                
        modify_date |= edit_all_cc_data(book.id, book, cc_to_save)

    if 'pubdate' in data and data['pubdate'] is not None:
        if data['pubdate']:
            try:
                book.pubdate = datetime.strptime(data['pubdate'], "%Y-%m-%d")
                modify_date = True
            except ValueError:
                book.pubdate = db.Books.DEFAULT_PUBDATE
        else:
            book.pubdate = db.Books.DEFAULT_PUBDATE
            modify_date = True

    if modify_date:
        book.last_modified = datetime.now(timezone.utc)
        kobo_sync_status.remove_synced_book(book.id, all=True)
        calibre_db.set_metadata_dirty(book.id)
        
    try:
        calibre_db.session.merge(book)
        calibre_db.session.commit()
    except Exception as e:
        calibre_db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
    return get_book_detail(book.id)

@api_v1.route('/shelves', methods=['GET'])
@login_required_if_no_ano
def get_shelves():
    if not current_user.is_authenticated or current_user.is_anonymous:
        shelves = ub.session.query(ub.Shelf).filter(ub.Shelf.is_public == 1).order_by(ub.Shelf.name).all()
    else:
        shelves = ub.session.query(ub.Shelf).filter(
            (ub.Shelf.user_id == current_user.id) | (ub.Shelf.is_public == 1)
        ).order_by(ub.Shelf.name).all()
        
    return jsonify([{
        "id": s.id,
        "name": s.name,
        "is_public": bool(s.is_public),
        "kobo_sync": bool(s.kobo_sync),
        "count": s.books.count()
    } for s in shelves])

@api_v1.route('/meta/custom-columns', methods=['GET'])
@login_required_if_no_ano
def get_custom_columns():
    cc = calibre_db.session.query(db.CustomColumns).filter(db.CustomColumns.datatype.notin_(db.cc_exceptions)).all()
    return jsonify([{
        "id": c.id,
        "label": c.label,
        "name": c.name,
        "datatype": c.datatype,
        "is_multiple": bool(c.is_multiple),
        "display": c.get_display_dict() if c.display else {}
    } for c in cc])

@api_v1.route('/session', methods=['GET'])
def get_session():
    user_data = None
    if current_user.is_authenticated and not current_user.is_anonymous:
        user_data = {
            "id": current_user.id,
            "nickname": current_user.name,
            "email": current_user.email,
            "role_admin": current_user.role_admin(),
            "role_edit": current_user.role_edit(),
            "role_download": current_user.role_download(),
            "role_upload": current_user.role_upload(),
            "locale": current_user.locale or "en"
        }
    
    locale = get_locale()
    locale_str = str(locale) if locale else "en"

    return jsonify({
        "user": user_data,
        "config": {
            "books_per_page": config.config_books_per_page,
            "authors_max": config.config_authors_max,
            "upload_enabled": bool(config.config_uploading),
            "kobo_enabled": bool(config.config_kobo_sync),
            "anonymous_browse": bool(config.config_anonbrowse == 1),
            "public_register": bool(config.config_public_reg)
        },
        "csrf_token": generate_csrf(),
        "locale": locale_str
    })

@api_v1.route('/login', methods=['POST'])
def api_login():
    if current_user.is_authenticated and not current_user.is_anonymous:
        return jsonify({
            "success": True,
            "user": {
                "id": current_user.id,
                "nickname": current_user.name,
                "email": current_user.email,
                "role_admin": current_user.role_admin(),
                "role_edit": current_user.role_edit(),
                "role_download": current_user.role_download(),
                "role_upload": current_user.role_upload(),
                "locale": current_user.locale or "en"
            }
        })

    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    remember_me = bool(data.get('remember_me', False))

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    from . import services
    from sqlalchemy import func
    from werkzeug.security import check_password_hash
    from .cw_login import login_user

    user = ub.session.query(ub.User).filter(func.lower(ub.User.name) == username).first()

    if config.config_login_type == constants.LOGIN_LDAP and services.ldap:
        login_result, error = services.ldap.bind_user(username, password)
        if login_result:
            login_user(user, remember=remember_me)
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "nickname": user.name,
                    "email": user.email,
                    "role_admin": user.role_admin(),
                    "role_edit": user.role_edit(),
                    "role_download": user.role_download(),
                    "role_upload": user.role_upload(),
                    "locale": user.locale or "en"
                }
            })
        elif login_result is None and user and check_password_hash(str(user.password), password) and user.name != "Guest":
            login_user(user, remember=remember_me)
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "nickname": user.name,
                    "email": user.email,
                    "role_admin": user.role_admin(),
                    "role_edit": user.role_edit(),
                    "role_download": user.role_download(),
                    "role_upload": user.role_upload(),
                    "locale": user.locale or "en"
                }
            })
        else:
            return jsonify({"error": "Wrong Username or Password"}), 401
    else:
        if user and check_password_hash(str(user.password), password) and user.name != "Guest":
            login_user(user, remember=remember_me)
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "nickname": user.name,
                    "email": user.email,
                    "role_admin": user.role_admin(),
                    "role_edit": user.role_edit(),
                    "role_download": user.role_download(),
                    "role_upload": user.role_upload(),
                    "locale": user.locale or "en"
                }
            })
        else:
            return jsonify({"error": "Wrong Username or Password"}), 401

@api_v1.route('/logout', methods=['POST'])
def api_logout():
    from .cw_login import logout_user
    logout_user()
    return jsonify({"success": True})

@api_v1.route('/register', methods=['POST'])
def api_register():
    if not config.config_public_reg:
        return jsonify({"error": "Public registration is disabled"}), 403

    if current_user.is_authenticated and not current_user.is_anonymous:
        return jsonify({"error": "Already logged in"}), 400

    data = request.get_json() or {}
    email = data.get('email', '').strip()
    name = data.get('username', '').strip()

    if not name or not email:
        return jsonify({"error": "Username and email are required"}), 400

    if config.config_register_email:
        nickname = email.lower()
    else:
        nickname = name

    try:
        nickname = helper.check_username(nickname)
        email = helper.check_email(email)
    except Exception as ex:
        return jsonify({"error": str(ex)}), 400

    from werkzeug.security import generate_password_hash
    content = ub.User()
    if helper.check_valid_domain(email):
        content.name = nickname
        content.email = email
        password = helper.generate_random_password(config.config_password_min_length)
        content.password = generate_password_hash(password)
        content.role = config.config_default_role
        content.locale = config.config_default_locale
        content.sidebar_view = config.config_default_show
        content.allowed_tags = config.config_allowed_tags
        content.denied_tags = config.config_denied_tags
        content.allowed_column_value = config.config_allowed_column_value
        content.denied_column_value = config.config_denied_column_value
        try:
            ub.session.add(content)
            ub.session.commit()
            
            from . import feature_support
            if feature_support.get('oauth'):
                from .oauth_bb import register_user_with_oauth
                if register_user_with_oauth:
                    register_user_with_oauth(content)
                    
            helper.send_registration_mail(email, nickname, password)
        except Exception as e:
            ub.session.rollback()
            return jsonify({"error": "An error occurred during registration: " + str(e)}), 500
    else:
        return jsonify({"error": "Your Email domain is not allowed"}), 400

    return jsonify({"success": True, "message": "Success! Registration details sent to your email."})

@api_v1.route('/config', methods=['GET'])
@login_required_if_no_ano
def api_get_config():
    if not current_user.role_admin():
        return jsonify({"error": "Admin access required"}), 403
    return jsonify({
        "config_calibre_dir": config.config_calibre_dir,
        "config_books_per_page": config.config_books_per_page,
        "config_calibre_web_title": config.config_calibre_web_title,
        "config_public_reg": bool(config.config_public_reg),
        "config_uploading": bool(config.config_uploading),
        "config_anonbrowse": bool(config.config_anonbrowse == 1)
    })

@api_v1.route('/config', methods=['POST'])
@login_required_if_no_ano
def api_post_config():
    if not current_user.role_admin():
        return jsonify({"error": "Admin access required"}), 403
    
    data = request.get_json() or {}
    import os
    
    if 'config_calibre_dir' in data:
        db_dir = data['config_calibre_dir'].strip()
        metadata_db = os.path.join(db_dir, "metadata.db")
        if not os.path.exists(metadata_db):
            return jsonify({"error": "DB Location is not Valid, metadata.db not found"}), 400
        
        if config.config_calibre_dir != db_dir:
            config.config_calibre_dir = db_dir
            calibre_db.setup_db(db_dir, ub.app_DB_path)
            
    if 'config_books_per_page' in data:
        try:
            config.config_books_per_page = int(data['config_books_per_page'])
        except ValueError:
            return jsonify({"error": "Invalid books per page value"}), 400
            
    if 'config_calibre_web_title' in data:
        config.config_calibre_web_title = data['config_calibre_web_title'].strip()
        
    if 'config_public_reg' in data:
        config.config_public_reg = bool(data['config_public_reg'])
        
    if 'config_uploading' in data:
        config.config_uploading = bool(data['config_uploading'])
        
    if 'config_anonbrowse' in data:
        config.config_anonbrowse = 1 if bool(data['config_anonbrowse']) else 0

    try:
        config.save()
    except Exception as e:
        return jsonify({"error": "Failed to save configuration: " + str(e)}), 500

    return jsonify({"success": True})

@api_v1.route('/admin/users', methods=['GET'])
@login_required_if_no_ano
def api_get_users():
    if not current_user.role_admin():
        return jsonify({"error": "Admin access required"}), 403
    users = ub.session.query(ub.User).all()
    return jsonify([{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role_admin": u.role_admin(),
        "role_edit": u.role_edit(),
        "role_download": u.role_download(),
        "role_upload": u.role_upload(),
        "locale": u.locale or "en"
    } for u in users])

@api_v1.route('/admin/users', methods=['POST'])
@login_required_if_no_ano
def api_create_user():
    if not current_user.role_admin():
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
        
    existing = ub.session.query(ub.User).filter(ub.User.name == username).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400
        
    from werkzeug.security import generate_password_hash
    user = ub.User()
    user.name = username
    user.email = email
    user.password = generate_password_hash(password)
    user.role = config.config_default_role
    user.locale = config.config_default_locale
    
    try:
        ub.session.add(user)
        ub.session.commit()
    except Exception as e:
        ub.session.rollback()
        return jsonify({"error": "Failed to create user: " + str(e)}), 500
        
    return jsonify({"success": True, "user_id": user.id})

@api_v1.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required_if_no_ano
def api_delete_user(user_id):
    if not current_user.role_admin():
        return jsonify({"error": "Admin access required"}), 403
    if user_id == current_user.id:
        return jsonify({"error": "Cannot delete yourself"}), 400
        
    user = ub.session.query(ub.User).get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    try:
        ub.session.delete(user)
        ub.session.commit()
    except Exception as e:
        ub.session.rollback()
        return jsonify({"error": "Failed to delete user: " + str(e)}), 500
        
    return jsonify({"success": True})


