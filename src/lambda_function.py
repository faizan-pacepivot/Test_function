import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# ------------------ ACCESS TOKEN ------------------
load_dotenv()


def get_access_token():
    url = "https://api.amazon.co.uk/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ['client_id'],
        "client_secret": os.environ['client_secret'],
        "refresh_token": os.environ['refresh_token'],
        "scope": "profile",
        "profile_id": os.environ['profile_id']
    }

    r = requests.post(url, data=data)
    print("Token Status:", r.status_code)

    if r.status_code != 200:
        raise Exception("Failed to get token")

    return r.json()["access_token"]


# ------------------ CAMPAIGN ------------------
def build_manual_campaign_payload(name, budget, dynamic_bidding, TOS_bidding, ROS_bidding, PP_bidding, AB_bidding):
    return {
        "campaigns": [
            {
                "name":     name,
                "campaignType": "SPONSORED_PRODUCTS",
                "targetingType": "MANUAL",
                "state": "ENABLED",
                "startDate": "2026-01-08",

                # 🔹 Placement Bidding
                "dynamicBidding": {
                    "placementBidding": [
                        {
                            "percentage": TOS_bidding,
                            "placement": "PLACEMENT_TOP"
                        },
                        {
                            "percentage": ROS_bidding,
                            "placement": "PLACEMENT_REST_OF_SEARCH"
                        },
                        {
                            "percentage": PP_bidding,
                            "placement": "PLACEMENT_PRODUCT_PAGE"
                        },
                        {
                            "percentage": AB_bidding,
                            "placement": "SITE_AMAZON_BUSINESS"
                        },

                    ],
                    "strategy": dynamic_bidding
                },
                "budget": {
                    "budgetType": "DAILY",
                    "budget": budget
                }
            }
        ]
    }


def create_campaign(name, budget, access_token, dynamic_bidding, TOS_bidding, ROS_bidding, PP_bidding, AB_bidding):
    url = "https://advertising-api-eu.amazon.com/sp/campaigns"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.environ['client_id'],
        "Amazon-Advertising-API-Scope": os.environ['profile_id'],
        "Content-Type": "application/vnd.spCampaign.v3+json",
        "Accept": "application/vnd.spCampaign.v3+json"
    }

    payload = build_manual_campaign_payload(
        name, budget, dynamic_bidding, TOS_bidding, ROS_bidding, PP_bidding, AB_bidding)

    r = requests.post(url, headers=headers, json=payload)
    print("Campaign Status:", r.status_code)
    print("Response:", r.text)

    data = r.json()
    return data["campaigns"]["success"][0]["campaignId"]


# ------------------ AD GROUP ------------------
def create_ad_group(campaign_id, name, default_bid, access_token):
    url = "https://advertising-api-eu.amazon.com/sp/adGroups"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.environ['client_id'],
        "Amazon-Advertising-API-Scope": os.environ['profile_id'],
        "Content-Type": "application/vnd.spAdGroup.v3+json",
        "Accept": "application/vnd.spAdGroup.v3+json"
    }

    payload = {
        "adGroups": [
            {
                "name": name,
                "campaignId": campaign_id,
                "defaultBid": default_bid,
                "state": "ENABLED"
            }
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    data = r.json()
    return data["adGroups"]["success"][0]["adGroupId"]


# ------------------ KEYWORD ------------------
def create_keyword(access_token, campaign_id, ad_group_id, keywords):
    """
    keywords = [
        {"text": "kids toy", "match_type": "EXACT", "bid": 2.0},
        {"text": "children toy", "match_type": "EXACT", "bid": 2.0},
        {"text": "baby toy", "match_type": "EXACT", "bid": 2.0}
    ]
    """
    url = "https://advertising-api-eu.amazon.com/sp/keywords"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.environ['client_id'],
        "Amazon-Advertising-API-Scope": os.environ['profile_id'],
        "Content-Type": "application/vnd.spKeyword.v3+json",
        "Accept": "application/vnd.spKeyword.v3+json"
    }

    payload = {
        "keywords": []
    }

    for kw in keywords:
        payload["keywords"].append({
            "campaignId": campaign_id,
            "adGroupId": ad_group_id,
            "keywordText": kw["text"],
            "matchType": kw["match_type"],
            "bid": kw["bid"],
            "state": "ENABLED"
        })

    r = requests.post(url, headers=headers, json=payload)
    print("Keyword Status:", r.status_code)
    print("Keyword Response:", r.text)

    return [
        k["keywordId"]
        for k in r.json()["keywords"]["success"]
    ]


# ------------------ PRODUCT AD ------------------
def create_product_ad(campaign_id, ad_group_id, access_token, products):
    url = "https://advertising-api-eu.amazon.com/sp/productAds"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": os.environ['client_id'],
        "Amazon-Advertising-API-Scope": os.environ['profile_id'],
        "Content-Type": "application/vnd.spProductAd.v3+json",
        "Accept": "application/vnd.spProductAd.v3+json"
    }

    payload = {
        "productAds": [
            {
                "campaignId": campaign_id,
                "adGroupId": ad_group_id,
                "asin": p["asin"],
                "sku": p["sku"],
                "state": "ENABLED"
            } for p in products
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    return [p["adId"] for p in r.json()["productAds"]["success"]]


# ------------------ LAMBDA HANDLER ------------------
def lambda_handler(event, context):

    budget = 100

    # 🔹 Placement Bidding
    TOS_bidding = 50
    ROS_bidding = 30
    PP_bidding = 10
    AB_bidding = 10
    dynamic_bidding = "AUTO_FOR_SALES"
    default_bid = 3.0
    # keyword_text = "kids toy"
    # match_type = "EXACT"
    # bid = 2.0
    # sku = "EC-0IZA-WFCV"
    # asin = "B00DZL9HZU"
    access_token = get_access_token()

    keywords = [
        {"text": "kids toy", "match_type": "EXACT", "bid": 2.0},
        {"text": "children toy", "match_type": "EXACT", "bid": 2.0},
        {"text": "baby toy", "match_type": "EXACT", "bid": 2.0}
    ]

    products = [
        {"asin": "B00792NTR8", "sku": "0A-SLD7-P9Y1"},
        {"asin": "B007OUBIDC", "sku": "0B-S5LI-HUN6"},
        {"asin": "B009GCTRCU", "sku": "0L-Z03K-YKYE"}
    ]

    cid = create_campaign("Faizan4b", budget, access_token, dynamic_bidding,
                          TOS_bidding, ROS_bidding, PP_bidding, AB_bidding)
    agid = create_ad_group(cid, "Lambda Ad Group 2", default_bid, access_token)
    # kid = create_keyword(access_token, cid, agid, keyword_text, match_type, bid)
    kid = create_keyword(access_token, cid, agid, keywords)
    pid = create_product_ad(cid, agid, access_token, products)

    return {
        "campaignId": cid,
        "adGroupId": agid,
        "keywordId": kid,
        "productAdId": pid
    }


# ------------------ LOCAL TEST ------------------
if __name__ == "__main__":
    print("DEBUG STARTED")
    result = lambda_handler({}, {})
    print("FINAL RESULT:", result