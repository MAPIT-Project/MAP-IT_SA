import requests

link = "https://cordis.europa.eu/search?q=contenttype%3D%27project%27%20AND%20language%3D%27en%27%20AND%20startDate%3E2018-01-01%20AND%20(%27artificial%20intelligence%27%20OR%20%27AI%27%20OR%20%27healthcare%27)%20AND%20(%27Germany%27)&p=1&num=10&srt=Relevance:decreasing&archived=true"

r = requests.get(link)

with open("cordis_page.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print(r.status_code)