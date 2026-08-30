import re
import requests
from bs4 import BeautifulSoup

def main():
	page_num = 1
	witr_url = "http://logger.witr.rit.edu/?page="

	session = requests.Session()

	page = session.get(witr_url + str(page_num))

	while page.status_code == 200 :
		html = BeautifulSoup(page.text, 'html5lib')
		tr_tags = html.find_all("tr")

		for t in tr_tags:
			if 'id' in t.attrs and "track_" in t.attrs['id']:
				print striphtml(str(t.contents[1])) + " - " + striphtml(str(t.contents[3]))

		page_num = page_num + 1
		page = session.get(witr_url + str(page_num))

def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

if __name__ == "__main__":
    main()