import os
import requests
from dotenv import load_dotenv # can be installed with `pip install python-dotenv`

load_dotenv('.env.local')

NEYNAR_API_KEY = os.getenv('NEYNAR_API_KEY')
SIGNER_UUID = os.getenv('SIGNER_UUID')

def follow_users(target_fids):
    """
    Follow multiple Farcaster users by their FIDs
    
    Args:
        target_fids (list): List of FIDs to follow
        
    Returns:
        dict: The response from the Neynar API
    """
    url = "https://api.neynar.com/v2/farcaster/user/follow"
    
    payload = {
        "target_fids": target_fids,
        "signer_uuid": SIGNER_UUID
    }
    
    headers = {
        "accept": "application/json", 
        "content-type": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def get_trending_casts(channel_id=None, time_window="24h", limit=10):
    """
    Get trending casts from Farcaster
    
    Args:
        channel_id (str, optional): Channel ID to filter by
        time_window (str, optional): Time window for trending casts - '6h', '12h', or '24h' (default '24h')
        limit (int, optional): Number of casts to return (default 10)
        
    Returns:
        dict: The response from the Neynar API containing trending casts
    """
    base_url = "https://api.neynar.com/v2/farcaster/feed/trending"
    
    # Build query parameters
    params = {
        "limit": limit,
        "time_window": time_window,
        "provider": "neynar"
    }
    
    if channel_id:
        params["channel_id"] = channel_id
        
    headers = {
        "accept": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.get(base_url, headers=headers, params=params)
    return response.json()


def get_image_casts(limit=25):
    """
    Get casts containing images from the Farcaster feed
    
    Args:
        limit (int): Number of casts to return (default 25)
        
    Returns:
        dict: The response from the Neynar API containing image casts
    """
    url = f"https://api.neynar.com/v2/farcaster/feed?feed_type=filter&filter_type=embed_types&embed_types=image%2Fjpeg,image%2Fpng&with_recasts=true&limit={limit}"

    headers = {
        "accept": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.get(url, headers=headers)
    return response.json()


def react_cast(action, cast_hash):
    """
    React to a cast with either a like or recast
    
    Args:
        action (str): Either 'like' or 'recast'
        cast_hash (str): The hash of the cast to react to
        
    Returns:
        dict: The response from the Neynar API
    """
    url = "https://api.neynar.com/v2/farcaster/reaction"
    
    # Map action to reaction_type
    reaction_type = "like" if action == "like" else "recast"
    
    payload = {
        "signer_uuid": SIGNER_UUID,
        "reaction_type": reaction_type,
        "target": cast_hash
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json", 
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def post_cast(text, parent=None, channel_id=None):
    url = "https://api.neynar.com/v2/farcaster/cast"
    
    payload = {
        "signer_uuid": SIGNER_UUID,
        "text": text
    }
    
    if parent:
        payload["parent"] = parent
        
    if channel_id:
        payload["channel_id"] = channel_id

    headers = {
        "accept": "application/json", 
        "content-type": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def search_casts(query, limit=25):
    url = f"https://api.neynar.com/v2/farcaster/cast/search?q={query}&priority_mode=false&limit={limit}"
    
    headers = {
        "accept": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.get(url, headers=headers)
    return response.json()

def get_cast_details(cast_data):
    # cast_data = cast.get('cast', {})
    author = cast_data.get('author', {})
    bio = author.get('profile', {}).get('bio', {}).get('text')
    
    # Get image URL from embeds if available
    image_url = None
    embeds = cast_data.get('embeds', [])
    if embeds and len(embeds) > 0:
        embed = embeds[0]
        if 'metadata' in embed and 'content_type' in embed['metadata']:
            if embed['metadata']['content_type'].startswith('image/') and 'url' in embed:
                image_url = embed['url']
            
    return {
        'display_name': author.get('display_name'),
        'username': author.get('username'),
        'bio': bio,
        'text': cast_data.get('text'),
        'image_url': image_url
    }


def get_casts(identifier):
    url = f"https://api.neynar.com/v2/farcaster/cast?identifier={identifier}&type=hash"
    
    headers = {
        "accept": "application/json",
        "x-api-key": NEYNAR_API_KEY
    }

    response = requests.get(url, headers=headers)
    return response.json()
