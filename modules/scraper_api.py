import googlemaps
from datetime import datetime

def fetch_reviews(place_id, api_key):
    gmaps = googlemaps.Client(key=api_key)
    # Places Details 回傳評論
    details = gmaps.place(place_id=place_id, fields=['reviews'])
    reviews = details.get('result', {}).get('reviews', [])
    parsed = []
    for r in reviews:
        parsed.append({
            'author': r['author_name'],
            'rating': r['rating'],
            'time': datetime.fromtimestamp(r['time']),
            'text': r['text']
        })
    return parsed
