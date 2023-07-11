import re
import os
import time
import requests
from bs4 import BeautifulSoup
from tenacity import wait_random_exponential, stop_after_delay, retry, retry_if_not_exception_type
from vamtb.vamex import HubResponse
#import pyrfc6266

from vamtb.log import *
from vamtb.utils import *

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

    @retry(wait=wait_random_exponential(multiplier=2, max=30), stop=stop_after_delay(60), retry=retry_if_not_exception_type(KeyboardInterrupt))
    def get(self, url, **kwargs):
        #FIXME this shouldn't be needed
        HubMgr.__session.cookies['vamhubconsent'] = "yes"
        try:
            res = HubMgr.__session.get(url, **kwargs)
            if not( 
                200 <= res.status_code < 300 or
                (res.status_code in (301,303) and kwargs.get("allow_redirects") == False)):
                warn(f"Getting url {url} returned status code {res.status_code}")
                raise HubResponse
        except requests.exceptions.ConnectionError as e:
            warn(f"While getting {url} we got a connection error")
            raise
        return res

    @retry(wait=wait_random_exponential(multiplier=2, max=30), stop=stop_after_delay(60), retry=retry_if_not_exception_type(KeyboardInterrupt))
    def post(self, url, **kwargs):
        #FIXME this shouldn't be needed
        HubMgr.__session.cookies['vamhubconsent'] = "yes"
        try:
            res = HubMgr.__session.post(url, **kwargs)
            if not( 200 <= res.status_code < 300 ):
                warn(f"Getting url {url} returned status code {res.status_code}")
                raise HubResponse
        except requests.exceptions.ConnectionError as e:
            warn(f"While posting {url} we got a connection error")
            raise
        return res

    def write_var(self, file_name, content):
        if os.path.exists(file_name):
            warn(f"{file_name} already exists, not overwritting")
            return

        with open(file_name, 'wb') as fd:
            fd.write(content)
        print(green(f" > Downloaded {file_name} [{toh(os.path.getsize(file_name))}]"))

    def dl_file(self, url):
        print(f" > Downloading from {url}...")

        response = self.get(url)
        if 200 <= response.status_code < 300:
           pass 
        else:
            error(f"Getting url {url} returned status code {response.status_code}")
            debug(response.text)
            return
        file_names = []
        try:
            #FIXME
            #file_name = pyrfc6266.requests_response_to_filename(response)
            file_name = response.headers['content-disposition'][:-2].split('=')[1][1:]
            if not file_name.endswith("depend.txt"):
                self.write_var(file_name, response.content)
        except KeyError:
            # No content disposition
            # Might be multiple downloads
            # FIXME that's horrible
            content = response.text
            mult_links = self.get_links(content)
            for l in mult_links:
                self.dl_file(f"{base_url}/{l}")
            return

    def get_links(self, page_text):
        bs = BeautifulSoup(page_text, "html.parser")
        dl_a = [ a for a in bs.find_all('a', href=True) if a.text == "Download" ]
        res = [ a.get('href') for  a in dl_a if "/download" in a.get('href')]
        return res

    def get_token(self):
        resource_url = f"https://hub.virtamate.com/members/"
        try:
            page = self.get(resource_url)
        except:
            error(f"Couldn't get token from hub")
            return None

        page_text = page.text
        bs = BeautifulSoup(page_text, "html.parser")
        tk_el = bs.find(attrs={"name": "_xfToken"})
        return tk_el.get("value", None)

    def get_creator_uid(self, creator):
        """
        Get creator uid from creator name
        """
        info(f"Getting creator uid for {creator}")
        tk = self.get_token()
        if not tk:
            error("Couldn't get token from hub")
            return None
        else:
            debug(f"Got hub token {tk}")

        resource_url = "https://hub.virtamate.com/members"
        try:
            page = self.post(resource_url, data = {"username": creator, "_xfToken": tk} )
        except: 
            error(f"Couln't get member {creator} from hub")
            return None

        resource_page = page.text
        soup = BeautifulSoup(resource_page, "html.parser")
        #TODO quick and dirty
        res = soup.find(href=re.compile("/search/member\\?user_id=.*"))
        if res:
            uid = res.get("href").replace("/search/member?user_id=", "")
            return f"{creator.lower()}.{uid}"
        else:
            error(f"Didn't find member {creator}")
            return None

    def dl_resource(self, resource_url):
        """
        Download a resource
        """
        try:
            page = self.get(resource_url)
        except:
            error(f"Couln't download resource from {resource_url}")
            return

        dl_links = self.get_links(page.text)
        if len(dl_links) > 1:
            error(f"We got more than one download link for {resource_url}, please check {','.join(dl_links)}")
        elif not dl_links:
            # Paid link
            print(f" > {resource_url} can't be downloaded (offsite)")
            return
        else:
            self.dl_file(f"{base_url}/{dl_links[0]}")

    def get_resources_from_author(self, creator, creatoruid=None, cooldown_seconds=60, resource_name=None):
        """
        Get resources links from creator
        """
        resource_found = False
        if not creatoruid:
            hubname = get_hub_name(creator)
            creator = self.get_creator_uid(hubname or creator)
            if not creator:
                return
        for page in range(1,101):
            url = f"{base_resource_per_author_url}/{creator}/?page={page}"

            try:
                check_end = self.get(url, allow_redirects=False)
            except:
                error(f"Couldn't fetch page {page} for resource of member {creator}")
                return
            if check_end.status_code == 303:
                break
            info(f"Fetching resources from {url}")
            try:
                page = self.get(url)
            except:
                error(f"Couldn't fetch page {page} for resource of member {creator}")
                return

            bs = BeautifulSoup(page.text, "html.parser")
            regexp = re.compile(r"/resources/[^/]*/$")
            links = [ f.get('href') for f in bs.find_all('a', href=True) ]
            links = list(set([ f[1:] for  f in links if re.match(regexp, f)]))
            if resource_name:
                reduced_list = [ l for l in links if resource_name.lower() in l.lower() ]
                links = reduced_list
                if links:
                    resource_found = True
            idx = 0
            ntry = 3
            while idx < len(links) and ntry:
                try:
                    self.dl_resource(f"{base_url}/{links[idx]}")
                    idx = idx + 1
                except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
                    ntry = ntry - 1
                    warn(f"Got {e}, waiting {cooldown_seconds}s, remaining attempts:{ntry}")
                    time.sleep(cooldown_seconds)
        if resource_name and not resource_found:
            print(f"Resource {resource_name} not found")