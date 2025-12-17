import json
import os

import requests
from flask import Blueprint, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import db, User, create_default_accounts_for_user
from oauthlib.oauth2 import WebApplicationClient
from datetime import datetime

google_auth = Blueprint("google_auth", __name__)

def get_google_client():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        return None
    return WebApplicationClient(client_id)

def get_google_provider_cfg():
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    try:
        return requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
    except:
        return None

@google_auth.route("/google_login")
def login():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        flash("Google login is not configured. Please use email/password login.", "warning")
        return redirect(url_for("auth.login"))
    
    client = get_google_client()
    google_provider_cfg = get_google_provider_cfg()
    
    if not google_provider_cfg:
        flash("Could not connect to Google. Please try again later.", "danger")
        return redirect(url_for("auth.login"))
    
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        flash("Google login is not configured.", "danger")
        return redirect(url_for("auth.login"))
    
    client = get_google_client()
    code = request.args.get("code")
    
    if not code:
        flash("Authorization failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))
    
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        flash("Could not connect to Google. Please try again later.", "danger")
        return redirect(url_for("auth.login"))
    
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url.replace("http://", "https://"),
        redirect_url=request.base_url.replace("http://", "https://"),
        code=code,
    )
    
    try:
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(client_id, client_secret),
            timeout=10
        )
        client.parse_request_body_response(json.dumps(token_response.json()))
    except Exception as e:
        flash("Authentication failed. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    
    try:
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)
        userinfo = userinfo_response.json()
    except:
        flash("Could not get user information from Google.", "danger")
        return redirect(url_for("auth.login"))

    if not userinfo.get("email_verified"):
        flash("Your Google email is not verified.", "danger")
        return redirect(url_for("auth.login"))
    
    google_id = userinfo["sub"]
    users_email = userinfo["email"]
    users_name = userinfo.get("name", userinfo.get("given_name", "User"))
    profile_picture = userinfo.get("picture", "")

    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        user = User.query.filter_by(email=users_email).first()
        if user:
            user.google_id = google_id
            user.profile_picture = profile_picture
            db.session.commit()
        else:
            username = users_email.split('@')[0]
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=users_email,
                full_name=users_name,
                google_id=google_id,
                profile_picture=profile_picture,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            create_default_accounts_for_user(user.id)
            flash(f"Welcome {users_name}! Your account has been created.", "success")

    if not user.is_active:
        flash("Your account has been deactivated.", "danger")
        return redirect(url_for("auth.login"))
    
    login_user(user, remember=True)
    user.last_login = datetime.utcnow()
    db.session.commit()

    return redirect(url_for("dashboard.index"))


@google_auth.route("/google_logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))
