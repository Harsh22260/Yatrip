# Image credits

Every photograph shipped in this folder is freely licensed and was downloaded
from Wikimedia Commons or Unsplash. Attribution is required by most of these
licences (CC BY / CC BY-SA), so keep this file alongside the images.

Machine-readable version: [`credits.json`](./credits.json)

| File | Subject | Author | Licence |
| --- | --- | --- | --- |
| `hero/india.jpg` | Taj Mahal | Yann, edited by Jim Carter | CC BY-SA 4.0 |
| `destinations/rajasthan.jpg` | Hawa Mahal, Jaipur | Chainwit. | CC BY-SA 4.0 |
| `destinations/kerala.jpg` | Backwaters, Alappuzha | Augustus Binu | CC BY-SA 3.0 |
| `destinations/goa.jpg` | Palolem Beach, South Goa | iMahesh | CC BY-SA 4.0 |
| `destinations/himachal.jpg` | Kullu Valley near Manali | UnpetitproleX | CC BY-SA 4.0 |
| `destinations/varanasi.jpg` | Dashashwamedh Ghat | Saaremees | CC BY-SA 4.0 |
| `destinations/ladakh.jpg` | Hemis Monastery | Bernard Gagnon | CC BY-SA 4.0 |
| `categories/hotels.jpg` | Lake Palace, Udaipur | user:Flicka | CC BY-SA 3.0 |
| `categories/attractions.jpg` | Amber Fort, Jaipur | Jakub Hałun | CC BY-SA 4.0 |
| `categories/food.jpg` | Indian thali | Unsplash contributor | Unsplash License |
| `categories/transport.jpg` | Delhi Metro, Yellow Line | WillaMissionary | CC0 |
| `categories/rentals.jpg` | Royal Enfield | Gpkp | CC BY-SA 4.0 |
| `auth/panel.jpg` | Jaisalmer Fort | Gérard Janot | CC BY-SA 3.0 |

## Re-fetching

These were pulled with the Wikipedia REST summary API to locate the Commons
file, then the Commons API with `iiurlwidth=1280` to obtain a thumbnail URL that
actually exists:

```
GET https://en.wikipedia.org/api/rest_v1/page/summary/<Article>
GET https://commons.wikimedia.org/w/api.php
      ?action=query&titles=File:<Name>&prop=imageinfo
      &iiprop=url|extmetadata|size&iiurlwidth=1280&format=json
```

Two things to know if you re-run this:

- Do **not** hand-edit a thumbnail URL to change its width. Wikimedia only
  serves a fixed set of pre-generated sizes per file, so arbitrary widths
  (`640px`, `1024px`) return `400 Bad Request`. Ask the API for the size instead.
- The Commons API rate-limits aggressively. Space requests by ~9 seconds or you
  will get `429` partway through the batch.

Note that article lead images are not curated. `Pangong_Tso` resolves to an ISS
satellite photograph of the region, which is why Ladakh points at
`Hemis_Monastery` instead.

## Optimising

`frontend/scripts/optimize_images.py` resizes each photo to the width it is
actually displayed at and re-saves it as a progressive JPEG. Run it after
swapping any image in:

```
venv\Scripts\python.exe frontend\scripts\optimize_images.py
```

It rewrites `credits.json` with the final dimensions as a side effect, so the
attribution stays in step with what is on disk. It brought the folder from
3.8 MB to 1.4 MB.