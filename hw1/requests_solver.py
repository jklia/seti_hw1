import re
import time
import requests

token = "4b2cd3db52761f1e2ab325b429d2544c"
host = "hw1.alexbers.com"
base_url = f"http://{host}"

session = requests.Session()
session.cookies.set("user", token)
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Connection": "close",})


def extract_link(body):
    link = re.search(r'href=[\'"]([^\'"]+)[\'"]', body)
    if link:
        return link.group(1)

    link = re.search(r"<code>(/[^<]+)</code>", body)
    if link:
        return link.group(1)

    return "/"


def extract_cookies(body):
    cookies_match = re.search(
        r"cookie:.*?(<table.*?>.*?</table>)", body, re.DOTALL | re.IGNORECASE
    )
    cookies_dict = {}
    if cookies_match:
        cookie_pairs = re.findall(
            r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>",
            cookies_match.group(1),
        )
        for key, val in cookie_pairs:
            cookies_dict[key] = val

    return cookies_dict


def extract_headers(body):
    extra_headers = {}
    headers_match = re.search(
        r"следующие заголовки:.*?(<table.*?>.*?</table>)", body, re.DOTALL
    )
    if headers_match:
        headers_table = headers_match.group(1)
        header_pairs = re.findall(
            r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>", headers_table
        )
        for key, val in header_pairs:
            extra_headers[key] = val
    return extra_headers


def extract_query_params(body):
    query_params_dict = {}
    params_match = re.search(
        r"При переходе выставьте следующие параметры запроса, указанные в таблице:.*?(<table.*?>.*?</table>)",
        body,
        re.DOTALL,
    )
    if params_match:
        params_table = params_match.group(1)
        params_pairs = re.findall(
            r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>", params_table
        )
        for key, val in params_pairs:
            query_params_dict[key] = val
    return query_params_dict


def extract_token(body):
    match = re.search(r"ключ:.*?<code>(.*?)</code>", body)
    if match:
        return match.group(1)
    return ""

def extract_page_step(body):
    match = re.search(r"Шаг\s*#(\d+)", body, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


url = base_url + "/"
kwargs = {}
method = "get"

while True:
    try:
        if method == "get":
            response = session.get(url, timeout=(10.0, 10.0), **kwargs)
        else:
            response = session.post(url, timeout=(10.0, 10.0), **kwargs)
    except requests.exceptions.RequestException as e:
        print(f"timeout или ошибка сети {e}")
        time.sleep(2.0)
        continue


    if response.status_code != 200:
        print(f"ошибка HTTP {response.status_code}")
        print(response.text)
        break

    html_body = response.text
    # step = extract_page_step(response.text) # вывод шагов
    # print(f"Step {step}")

    if "ключ" in html_body:
        print(extract_token(html_body))
        break

    next_path = extract_link(html_body)
    url = base_url + next_path
    query_params = extract_query_params(html_body)
    headers = extract_headers(html_body)
    cookies = extract_cookies(html_body)

    kwargs = {"params": query_params, "headers": headers, "cookies": cookies}

    if "Загрузите" in html_body:
        method = "post"
        files_table_match = re.search(r"(<table.*?>.*?</table>)", html_body, re.DOTALL)
        table_html = files_table_match.group(1)
        file_pairs = re.findall(
            r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>", table_html
        )
        body_parts = []
        for filename, content in file_pairs:
            body_parts.append(
                (
                    "file",
                    (filename, content.encode("utf-8"), "application/octet-stream"),
                )
            )
        kwargs["files"] = body_parts

    elif "POST" in html_body:
        method = "post"
        form_data = re.search(
            r"данные формы:.*?(<table.*?>.*?</table>)", html_body, re.DOTALL
        )
        data_pairs = re.findall(
            r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>",
            form_data.group(1),
        )
        data_pairs_dict = {}
        for key, value in data_pairs:
            data_pairs_dict[key] = value
        kwargs["data"] = data_pairs_dict

    elif "Перейдите" in html_body or "GET" in html_body:
        method = "get"
    else:
        print("не реализовано")
        print(html_body)
        break

    time.sleep(1.0)


