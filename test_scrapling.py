from scrapling.fetchers import Fetcher

# HTTP request biasa
page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()

for q in quotes[:3]:
    print(q)