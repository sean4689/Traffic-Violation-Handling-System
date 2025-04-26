import requests

access_token=""

def get_coordinates(address, access_token):
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {
        'access_token': access_token,
        'limit': 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'features' in data and len(data['features']) > 0:
        coordinates = data['features'][0]['geometry']['coordinates']
        return coordinates
    else:
        return None

print(get_coordinates("台北市中正區信義路二段23號", access_token))
