import re
import os
import time
import requests
from bs4 import BeautifulSoup
import pyrfc6266

from vamtb.log import *

base_url = "https://hub.virtamate.com"
base_resource_url = f"{base_url}/resources"
base_resource_per_author_url = f"{base_resource_url}/authors"

class HubMgr:

    __session = None

    def __init__(self):
        HubMgr.__session = requests.Session()
        #TODO ask user once, set in conf
        HubMgr.__session.cookies['vamhubconsent'] = "yes"
        HubMgr.__session.headers.update({'User-Agent': 'Vamtb see https://github.com/vaminator/vamtb'})

    def get(self, url, **kwargs):
        #FIXME this shouldn't be needed
        HubMgr.__session.cookies['vamhubconsent'] = "yes"
        return HubMgr.__session.get(url, **kwargs)

    def dl_file(self, url):
        print(f" > Downloading from {url}...")

        response = self.get(url)
        if 200 <= response.status_code <= 299:
           pass 
        else:
            error(f"Getting url {url} returned status code {response.status_code}")
            debug(response.text)
            return
        try:
            #FIXME
            #file_name = pyrfc6266.requests_response_to_filename(response)
            file_name = response.headers['content-disposition'][:-2].split('=')[1][1:]
        except Exception as e:
            print(e)
            print(response.text)
            return

        if os.path.exists(file_name):
            warn(f"{file_name} already exists, not overwritting")
            return

        with open(file_name, 'wb') as fd:
            fd.write(response.content)
        print(green(f" > Downloaded {file_name}"))

    def dl_resource(self, resource_url):
        """
        Download a resource
        """
        page = self.get(resource_url)
        if 200 <= page.status_code <= 299:
           debug(f"{page.text}") 
        else:
            critical(f"Getting url {resource_url} returned status code {page.status_code}")
        resource_page = page.text
        
        regexp = re.compile(r"/download" + "$")
        bs = BeautifulSoup(resource_page, "html.parser")
        dl_a = [ a for a in bs.find_all('a', href=True) if a.text !="Go to pay site" ]
        dl_links = sorted(list(set([ a.get('href') for  a in dl_a if a.get('href').endswith('/download')])))
        if len(dl_links) > 1:
            critical(f"We got more than one download link for {resource_url}, please check")
        elif not dl_links:
            # Paid link
            print(f"{resource_url} is a paid link")
            return
        else:
            self.dl_file(f"{base_url}/{dl_links[0]}")

    def get_resources_from_author(self, creator, cooldown_seconds=60):
        """
        Get resources links from creator
        """
        for page in range(1,101):
            url = f"{base_resource_per_author_url}/{creator}/?page={page}"
            print(f"Fetching resources from {url}")

            check_end = self.get(url, allow_redirects=False)
            if check_end.status_code == 303:
                return
            page = self.get(url)
            if 200 <= page.status_code <= 299:
                debug(f"{page.text}") 
            else:
                critical(f"Getting url {url} returned status code {page.status_code}")
            text = page.text
            bs = BeautifulSoup(text, "html.parser")
            regexp = re.compile(r"/resources/[^/]*/$")
            links = [ f.get('href') for f in bs.find_all('a', href=True) ]
            links = list(set([ f[1:] for  f in links if re.match(regexp, f)]))
            idx = 0
            ntry = 3
            while idx < len(links) and ntry:
                try:
                    self.dl_resource(f"{base_url}/{links[idx]}")
                    idx = idx + 1
                    ntry = 3
                except requests.exceptions.ConnectTimeout:
                    ntry = ntry - 1
                    warn(f"Got timeout, waiting {cooldown_seconds}s, remaining attempts:{ntry}")
                    time.sleep(cooldown_seconds)
