import socket
import re
import string
import time

token = "4b2cd3db52761f1e2ab325b429d2544c"
host = "hw1.alexbers.com"


RE_LINK_HREF = re.compile(r'href=[\'"]([^\'"]+)[\'"]')
RE_LINK_CODE = re.compile(r"<code>(/[^<]+)</code>")
RE_COOKIES = re.compile(r"cookie:.*?(<table.*?>.*?</table>)", re.DOTALL | re.IGNORECASE)
RE_PAIRS = re.compile(r"<td><code>(.*?)</code></td>\s*<td><code>(.*?)</code></td>")
RE_HEADERS = re.compile(
    r"следующие заголовки:.*?(<table.*?>.*?</table>)", re.DOTALL | re.IGNORECASE
)
RE_QUERY_PARAMS = re.compile(
    r"При переходе выставьте следующие параметры запроса, указанные в таблице:.*?(<table.*?>.*?</table>)",
    re.DOTALL | re.IGNORECASE,
)
RE_FORM_DATA = re.compile(
    r"данные формы:.*?(<table.*?>.*?</table>)", re.DOTALL | re.IGNORECASE
)
RE_FILE_DATA = re.compile(
    r"\(использовать кодировку UTF8 без BOM\):.*?(<table.*?>.*?</table>)",
    re.DOTALL | re.IGNORECASE,
)


def extract_link(body):
    link = RE_LINK_HREF.search(body)
    if link:
        return link.group(1)

    link = RE_LINK_CODE.search(body)
    if link:
        return link.group(1)

    return "/"


def extract_cookie(body):
    cookies_match = RE_COOKIES.search(body)
    all_cookies = {"user": token}
    if cookies_match:
        cookie_pairs = RE_PAIRS.findall(cookies_match.group(1))
        for key, val in cookie_pairs:
            all_cookies[key] = val

    return "; ".join([f"{k}={v}" for k, v in all_cookies.items()])


def extract_headers(body):
    extra_headers = []
    headers_match = RE_HEADERS.search(body)
    if headers_match:
        headers_table = headers_match.group(1)
        header_pairs = RE_PAIRS.findall(headers_table)
        for key, val in header_pairs:
            extra_headers.append(f"{key}: {val}")
    return extra_headers


def extract_query_params(body):
    query_params = []
    params_match = RE_QUERY_PARAMS.search(body)
    if params_match:
        params_table = params_match.group(1)
        params_pairs = RE_PAIRS.findall(params_table)
        for key, val in params_pairs:
            query_params.append(f"{encode_form_data(key)}={encode_form_data(val)}")
        return "?" + "&".join(query_params)
    return ""


def extract_token(body):
    match = re.search(r"ключ:.*?<code>(.*?)</code>", body, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def encode_form_data(data):
    alphabet = string.ascii_letters + string.digits + "_.-~"
    result = []
    for byte in data.encode("utf-8"):
        char = chr(byte)
        if char in alphabet:
            result.append(char)
        else:
            result.append(f"%{byte:02X}")
    return "".join(result)


def make_get_request(body):
    next_path = extract_link(body) + extract_query_params(body)

    extra_headers = extract_headers(body)
    cookie_header = extract_cookie(body)

    headers_list = [
        f"GET {next_path} HTTP/1.1",
        f"Host: {host}",
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        f"Cookie: {cookie_header}",
    ]

    headers_list.extend(extra_headers)
    headers_list.append("Connection: close")

    return ("\r\n".join(headers_list) + "\r\n\r\n").encode("utf-8")


def make_post_request(body):
    next_path = extract_link(body) + extract_query_params(body)

    form_data = RE_FORM_DATA.search(body)
    data_pairs = RE_PAIRS.findall(form_data.group(1))

    encoded_data_pairs = []
    for key, value in data_pairs:
        encoded_data_pairs.append(f"{encode_form_data(key)}={encode_form_data(value)}")

    post_body_bytes = "&".join(encoded_data_pairs).encode("utf-8")

    cookie_header = extract_cookie(body)
    extra_headers = extract_headers(body)

    headers_list = [
        f"POST {next_path} HTTP/1.1",
        f"Host: {host}",
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        f"Content-Type: application/x-www-form-urlencoded",
        f"Content-Length: {len(post_body_bytes)}",
        f"Cookie: {cookie_header}",
    ]

    headers_list.extend(extra_headers)
    headers_list.append("Connection: close")

    return ("\r\n".join(headers_list) + "\r\n\r\n").encode("utf-8") + post_body_bytes


def make_upload_files_request(body):
    next_path = extract_link(body) + extract_query_params(body)

    files_table_match = RE_FILE_DATA.search(body)
    file_pairs = RE_PAIRS.findall(files_table_match.group(1))

    boundary = "pipipicoolboundary12345676767689"

    body_parts = []
    for filename, content in file_pairs:
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(
                "utf-8"
            )
        )
        body_parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
        body_parts.append(content.encode("utf-8"))
        body_parts.append(b"\r\n")

    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    post_body_bytes = b"".join(body_parts)

    cookie_header = extract_cookie(body)
    extra_headers = extract_headers(body)

    headers_list = [
        f"POST {next_path} HTTP/1.1",
        f"Host: {host}",
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        f"Content-Type: multipart/form-data; boundary={boundary}",
        f"Content-Length: {len(post_body_bytes)}",
        f"Cookie: {cookie_header}",
    ]

    headers_list.extend(extra_headers)
    headers_list.append("Connection: close")

    return ("\r\n".join(headers_list) + "\r\n\r\n").encode("utf-8") + post_body_bytes


def extract_page_step(body):
    match = re.search(r"Шаг\s*#(\d+)", body, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


request = (
    "GET / HTTP/1.1\r\n"
    f"Host: {host}\r\n"
    f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
    f"Cookie: user={token}\r\n"
    "Connection: close\r\n\r\n"
).encode("utf-8")

while True:
    response = b""
    try:
        s = socket.create_connection((host, 80), timeout=5.0)
        s.settimeout(10.0)
        s.sendall(request)

        while True:
            try:
                chunk = s.recv(1024)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break
        s.close()
    except Exception as e:
        print(e)
        time.sleep(5.0)
        continue

    if not response:
        print("---- ошибка соединения с сервером, повтор отправки ----")
        time.sleep(5.0)
        continue

    resp_text = response.decode("utf-8")
    headers, _, html_body = resp_text.partition("\r\n\r\n")
    status_line = headers.split("\r\n")[0] if headers else ""

    if "200" not in headers:
        print(f"HTTP ошибка, сервер вернул: {status_line}")
        print(html_body)
        break

    if "ключ" in html_body:
        print(extract_token(html_body))
        break

    # page_step = extract_page_step(html_body) # вывод шагов
    # print(f"Шаг: {page_step}")

    if "Загрузите" in html_body:
        request = make_upload_files_request(html_body)
    elif "POST" in html_body:
        request = make_post_request(html_body)
    elif "Перейдите" in html_body or "GET" in html_body:
        request = make_get_request(html_body)
    else:
        print("Новый тип запроса:")
        print(html_body)
        break

    time.sleep(0.5)



