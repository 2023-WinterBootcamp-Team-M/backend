import re
import json
import openai
import environ
import requests
import urllib
import urllib.request
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from accountinfo.models import accountinfo
from bookmark.models import BookmarkFolder, Bookmark


# Create your views here.

env = environ.Env()
env.read_env()

def call_chatgpt_api(bookmark_url,user_id):
    openai.api_key = env('OPENAI_API_KEY')

    categorize_request = ("Based on the URL and name, create folder names that fit the category and output this in JSON format.\
                          Only include the input values we provided, without any examples.\
                          If it's difficult to categorize a folder into these classifications, label it as 'Others'.\
                          Please ensure that all folder names are summarized in just one word.\
                          The language of the folder name is Korean.\
                          If one bookmark is added, please include this data in the categories we identified earlier.\
                          Please provide the output in JSON format.\
                          This is the important thing. Please follow the rules.\
                          If the URL of the site includes words like naver, google, daum, categorize it as a portal.\
                          If it contains words like edu, ac.kr, categorize it as education. If it includes github, stackoverflow, categorize it as development.\
                          Please answer in Korean.")


    # folders = folder_data_list(user_id)
    # content = bookmark_url + ' '.join(folders) if folders else bookmark_url
    Flist = folder_data_list(user_id)

    # 폴더 이름과 해당 폴더에 속한 북마크 URL을 추출하여 content에 추가
    content = bookmark_url
    for folder_data in Flist:
        folder_name = folder_data['folder_name']
        bookmarks = folder_data['bookmarks']

        # 폴더 이름과 북마크 정보를 content에 추가
        content += f"\n폴더 이름: {folder_name}\n북마크 목록:\n"
        for bookmark in bookmarks:
            bookmark_name = bookmark['name']
            bookmark_url = bookmark['url']
            content += f"  - 북마크 이름: {bookmark_name}, 북마크 URL: {bookmark_url}\n"

    # 만약 폴더가 하나도 없다면, 기본 URL만 남깁니다.
    content = content if folder_data_list else bookmark_url


    response = openai.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {
                "role": "system",
                "content": categorize_request
            },
            {
                "role": "user",
                "content": content
            }
        ],
    )

    latest_response = response.choices[0].message.content.strip()

    # JSON 형식의 문자열 추출
    json_str_match = re.search(r"```json\n(.*)\n```", latest_response, re.DOTALL)
    if json_str_match:
        json_str = json_str_match.group(1).strip()

        # JSON 문자열 파싱
        try:
            json_data = json.loads(json_str)
            category = list(json_data.keys())[0]
            return category
        except json.JSONDecodeError:
            pass

    # 기본 카테고리 반환 (분석 실패 시)
    return "기타"



def new_bookmark(bookmark_name,bookmark_url, folder_id):
    folder_instance = BookmarkFolder.objects.get(id=folder_id)
    short_summary = summary_three(bookmark_url)
    long_summary = summary_six(bookmark_url)
    icon = icon_url(bookmark_url)

    bookmark = Bookmark(name=bookmark_name,url=bookmark_url,folder_id=folder_instance,
                        short_summary=short_summary, long_summary=long_summary)
    if icon is not None:
        bookmark.icon = icon

    bookmark.clean()
    bookmark.save()
    return bookmark
# def folder_name_list(user_id):
#     try:
#         user_id = User.objects.get(id=user_id)
#         folders = BookmarkFolder.objects.filter(user_id=user_id, deleted_at__isnull=True)
#         serializer = FolderSerializer(folders, many=True)
#
#         folder_names = [item['name'] for item in serializer.data]
#         return folder_names
#
#     except BookmarkFolder.DoesNotExist:
#         return None
def folder_data_list(user_id):
    try:
        user = accountinfo.objects.get(id=user_id)
        folders = BookmarkFolder.objects.filter(user_id=user, deleted_at__isnull=True)
        folder_data_list = []

        for folder in folders:
            folder_data = {
                'folder_name': folder.name,
                'bookmarks': [{'name': bookmark.name, 'url': bookmark.url} for bookmark in folder.bookmark_set.all()]
            }
            folder_data_list.append(folder_data)

        return folder_data_list

    except accountinfo.DoesNotExist:
        return None

# Based on the URL and name, create folder names that fit the category and output this in JSON format.\
#                           Only include the input values we provided, without any examples.\
#                           Rather than focusing on a single element like 'Developer Community' or 'Cloud Service Management', group such elements under broader categories like 'Development'. \
#                           Create folders from this wider perspective.\
#                           The language of the folder name is Korean.\
#                           If one bookmark is added, please include this data in the categories we identified earlier.\
#                           Please provide the output in JSON format.\
#                           Please answer in Korean.\

# Based on the URL and name, create folder names that fit the category and output this in JSON format. \
#     Only include the input values we provided, without any examples.\
#     The language of the folder name is Korean.\
#     If one bookmark is added, please include this data in the categories we identified earlier.\
#     Please provide the output in JSON format.\
#     lease answer in Korean.\


# Please categorize the contents of these links into about 10 categories and organize the links into each folder accordingly.\
#                           The language of the folder name is Korean.\
#                           If one bookmark is added, please include this data in the categories we identified earlier.\
#                           Please provide the output in JSON format.\
#                           Please answer in Korean.\

env = environ.Env()
env.read_env()

def crawl_url(url):
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ko-KR,kr;q=0.9, en-GB,en;q=0.9,en-US;q=0.8,hi;q=0.7,la;q=0.6',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'referer': 'https',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36',
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text()



def summary_three(url):
    try:
        openai.api_key = env('OPENAI_API_KEY')
        # data = json.loads(request.body)
        # url = data.get('url')

        content = crawl_url(url)

        # Adjust the request to OpenAI based on summary_length
        summary_request = ("Please summarize the entire text content in 140 characters.\
                           Please answer in Korean.")

        response = openai.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system",
                    "content": summary_request
                },
                {
                    "role": "user",
                    "content": content
                },
            ],
        )
        summary_content = response.choices[0].message.content
        return summary_content
    except Exception as e:
        return {'error': str(e)}


def summary_six(url):
    try:
        openai.api_key = env('OPENAI_API_KEY')
        # data = json.loads(request.body)
        #
        # url = data.get('url')

        content = crawl_url(url)

        # Adjust the request to OpenAI based on summary_length
        summary_request = ("Please summarize the entire text content in 280 characters.\
                            Please answer in Korean.")

        response = openai.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system",
                    "content": summary_request
                },
                {
                    "role": "user",
                    "content": content
                },
            ],
        )
        summary_content = response.choices[0].message.content
        return summary_content
    except Exception as e:
        return {'error': str(e)}

def check_favicon_url(url):
    try:
        response = requests.get(url)
        # HTTP 상태 코드가 200이면 페이지가 정상적으로 로드된 것으로 판단할 수 있습니다.
        if response.status_code >= 400 and response.status_code < 500:
            return 0
            # 여기에서 응답의 내용을 확인하고 원하는 값이 있는지 확인할 수 있습니다.
        else:
            return 1
    except:
        return 0

def icon_url(url):
    favicon = "http://www.google.com/s2/favicons?domain=" + url
    if check_favicon_url(favicon):
        return favicon
    else:
        return None

# 도메인 추출
# def extract_domain_from_url(url):
#     parsed_url = urlparse(url)
#     domain = parsed_url.netloc
#     return domain


