import requests
import json
import re

# =========================
# CONFIG
# =========================

API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
CLIENT_VERSION = "2.20231030.00.00"

SEARCH_URL = "https://www.youtube.com/youtubei/v1/search"
PLAYER_URL = "https://www.youtube.com/youtubei/v1/player"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# =========================
# HELPERS
# =========================

def get_text(obj):
    if not obj:
        return None
    if "simpleText" in obj:
        return obj["simpleText"]
    if "runs" in obj:
        return "".join(r.get("text", "") for r in obj["runs"])
    return None


def parse_view_count(text):
    if not text:
        return 0
    return int(re.sub(r"[^\d]", "", text))


def seconds_to_iso(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"PT{h}H{m}M{s}S"


# =========================
# SEARCH API
# =========================

def search_youtube(query, limit=3):
    body = {
        "query": query,
        "params": "EgIQAQ%3D%3D",  # videos only
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": CLIENT_VERSION
            }
        }
    }

    url = f"{SEARCH_URL}?key={API_KEY}&prettyPrint=false"
    r = requests.post(url, json=body, headers=HEADERS, timeout=10)
    r.raise_for_status()

    data = r.json()

    sections = (
        data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
    )

    results = []
    for section in sections:
        item_section = section.get("itemSectionRenderer")
        if not item_section:
            continue

        for item in item_section.get("contents", []):
            if "videoRenderer" in item:
                video_data = extract_search_video(item["videoRenderer"])
                results.append(video_data)
                if len(results) >= limit:
                    return results

    if not results:
        raise RuntimeError("No video results found")
    return results


def extract_search_video(vr):
    thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
    best_thumb = thumbs[-1]["url"] if thumbs else None

    return {
        "videoId": vr.get("videoId"),
        "title": get_text(vr.get("title")),
        "author": get_text(vr.get("ownerText")),
        "url": f"https://www.youtube.com/watch?v={vr.get('videoId')}",
        "thumbnail": best_thumb,
        "thumbnails": vr.get("thumbnail"),
        "isLive": False if not vr.get("badges") else "LIVE" in json.dumps(vr["badges"]),
        "viewCountText": get_text(vr.get("viewCountText"))
    }


# =========================
# PLAYER API
# =========================

def get_player_data(video_id):
    body = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": CLIENT_VERSION
            }
        }
    }

    url = f"{PLAYER_URL}?key={API_KEY}&prettyPrint=false"
    r = requests.post(url, json=body, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def extract_player_data(player):
    details = player.get("videoDetails", {})
    micro = player.get("microformat", {}).get("playerMicroformatRenderer", {})

    return {
        "description": details.get("shortDescription"),
        "videoTags": details.get("keywords", []),
        "duration": seconds_to_iso(details.get("lengthSeconds", 0)),
        "viewCount": int(details.get("viewCount", 0)),
        "maturity": "G" if micro.get("isFamilySafe", True) else "18+"
    }


# =========================
# MAIN MODULE FUNCTION
# =========================

def search_and_get_video_data(query, limit=3):
    """
    Search YouTube for videos and return complete video metadata.
    
    Args:
        query (str): Search query string
        limit (int): Maximum number of results to return (default: 3)
        
    Returns:
        list: List of complete video data dictionaries, each with the following fields:
            - author: Video author/channel name
            - description: Video description
            - duration: Video duration in ISO 8601 format (PT#H#M#S)
            - isLive: Boolean indicating if video is live
            - maturity: Content rating ("G" or "18+")
            - providerId: YouTube video ID
            - thumbnail: Best quality thumbnail URL (string)
            - thumbnails: Thumbnail object with {animated, channel, high} or None
            - title: Video title
            - url: YouTube watch URL
            - videoTags: List of video tags
            - viewCount: View count as integer
            
    Raises:
        RuntimeError: If no video results found
        requests.RequestException: If API requests fail
    """
    # Search for videos
    search_results = search_youtube(query, limit=limit)
    
    final_results = []
    for search_data in search_results:
        # Get detailed player data
        player_data = get_player_data(search_data["videoId"])
        player_fields = extract_player_data(player_data)
        
        # Merge all data into final result
        # Format thumbnails as expected by API: {animated: null, channel: null, high: url} or null
        thumbnail_url = search_data["thumbnail"]
        thumbnails_obj = None
        if thumbnail_url:
            thumbnails_obj = {
                "animated": None,
                "channel": None,
                "high": thumbnail_url
            }
        
        final_data = {
            "author": search_data["author"],
            "description": player_fields["description"],
            "duration": player_fields["duration"],
            "isLive": search_data["isLive"],
            "maturity": player_fields["maturity"],
            "providerId": search_data["videoId"],
            "thumbnail": thumbnail_url,  # Single thumbnail URL (high quality)
            "thumbnails": thumbnails_obj,  # Formatted object or null
            "title": search_data["title"],
            "url": search_data["url"],
            "videoTags": player_fields["videoTags"],
            "viewCount": player_fields["viewCount"]
        }
        
        final_results.append(final_data)
    
    return final_results


if __name__ == "__main__":
    print(search_and_get_video_data("The Beatles - Hey Jude"))
