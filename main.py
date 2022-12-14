from urllib.parse import unquote
import pandas as pd
import re
import requests
import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--headless")
driver = uc.Chrome()


def get_links(path: str):
    df = pd.read_excel(path)
    links = []
    for index, row in df.iterrows():
        links.append(row[0])
    print(links)
    return links


def get_links_for_1_task(link: str):
    i = 1
    links = []
    link_start = link.strip()
    while True:
        clean_link = unquote(link_start)
        clean_link = clean_link[:-1] + ',"pagination":{' + f'"currentPage":{i}' + "}}"
        html = get_html(clean_link)
        soup = BeautifulSoup(html, 'lxml')
        next_false = soup.find('a', {'title': 'Next page', 'tabindex': '-1'})
        links_page = re.findall('https://www.zillow.com/homedetails/.*?_zpid/', html)
        links.append(list(set(links_page)))
        pagination = soup.find('div', class_='search-pagination')
        if pagination is None:
            break
        i += 1
        print(clean_link)
        if next_false is None:
            continue
        else:
            break
    return links


def get_html_old(url):
    try:
        header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          "Chrome/74.0.3729.169 Safari/537.36",
            'referer': 'https://www.google.com/'
        }
        r = requests.get(url, headers=header).text
        return r
    except requests.exceptions.ConnectionError:
        print('повтор', time.strftime("%Y-%m-%d-%H.%M.%S", time.localtime()))
        time.sleep(10)
        get_html_old(url)


def get_html(url: str):
    try:
        driver.get(url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        html = driver.page_source

        return html
    except TypeError:
        get_html(url)


def get_data(html: str, link: str):
    soup = BeautifulSoup(html, 'lxml')

    try:
        address = soup.find_all('h1', class_='Text-c11n-8-73-0__sc-aiai24-0 kHeRng')[0].text
    except TypeError:
        address = ''

    seller = ''
    status = ''
    foreclosure = ''
    try:
        response = soup.find_all('span', class_='Text-c11n-8-73-0__sc-aiai24-0 dpf__sc-1yftt2a-1 kHeRng iOiapS')[0].text
        if response == 'For sale by owner':
            seller = response
            status = 'Sale'
        elif response == 'For sale':
            seller = response + ' by agent'
            status = 'Sale'
        elif response == 'Pre-foreclosure':
            seller = response
            status = response
            foreclosure = response
        elif response == 'Off market':
            status = response
        else:
            seller = response
            status = response
            foreclosure = response
    except TypeError:
        pass

    try:
        price = soup.find_all('span', class_='Text-c11n-8-73-0__sc-aiai24-0 dpf__sc-1me8eh6-0 kGdfMs fzJCbY')[0].text
    except TypeError:
        price = ''

    try:
        zestimate = soup.find_all('span', class_='Text-c11n-8-73-0__sc-aiai24-0 QDBWk')[0].text
    except TypeError:
        zestimate = ''

    try:
        days = soup.find_all('dl', class_='hdp__sc-7d6bsa-0 cUSEtc')[0].find_all('dt')[0].text
    except TypeError:
        days = ''

    try:
        views = soup.find_all('dl', class_='hdp__sc-7d6bsa-0 cUSEtc')[0].find_all('dt')[1].text
    except TypeError:
        views = ''

    try:
        saves = soup.find_all('dl', class_='hdp__sc-7d6bsa-0 cUSEtc')[0].find_all('dt')[2].text
    except TypeError:
        saves = ''
    try:
        description = soup.find_all('ul', class_='dpf__sc-xzpkxd-0 kExvOu')[0]
        plot = ''
        for row in description:
            plot += row.find('span', class_='Text-c11n-8-73-0__sc-aiai24-0 dpf__sc-2arhs5-3 kHeRng btxEYg').text + '\n'
        overview = soup.find_all('div', class_='Text-c11n-8-73-0__sc-aiai24-0 sc-cZMNgc kHeRng fvaIwQ')[0].text
        description_full = plot + '\n' + overview
    except TypeError:
        description_full = ''

    price_history = ''
    tax_history = ''
    try:
        table_price_history = soup.find_all('table', class_='hdp__sc-f00yqe-2 cQFnnD')[0]
        for tr in table_price_history.find('tbody').find_all('tr'):
            row = ''
            for td in tr:
                row += td.text + ' '
            price_history += row + '\n'
    except TypeError:
        pass

    try:
        table_tax_history = soup.find('table', class_='hdp__sc-f00yqe-2 kkEhCu')
        for tr in table_tax_history.find('tbody').find_all('tr'):
            row = ''
            for td in tr:
                row += td.text + ' '
            tax_history += row + '\n'
    except TypeError:
        pass

    price_with_tax = price_history + '\n' + tax_history
    return {
        'Ссылка': link,
        'Адрес объекта': address,
        'Цена': price,
        'Zestimate': zestimate,
        'Кто продает агент/собственник': seller,
        'Телефон собственника': '',
        'Статус': status,
        'Сколько времени на сайте ': days,
        'Количество просмотров ': views,
        'Сколько раз сохранили ': saves,
        'Описание': description_full,
        'Foreclosure information': foreclosure,
        'Price and tax history': price_with_tax
    }


def write_data_2_task(data: dict, file_path: str):
    df_file = pd.read_excel(file_path)
    link = data['Ссылка']
    index = df_file[df_file['Ссылка'] == link].index[0]
    df = pd.DataFrame([data], index=[index])
    df_file.update(df)
    df_file.to_excel(file_path, index=False)


def write_data_1_task(data: dict, file_path: str):
    df = pd.DataFrame([data])
    df_file = pd.read_excel(file_path)
    df_full = pd.concat([df_file, df])
    df_full.to_excel(file_path, index=False)


def main():
    print("Выберете режим работы скрипта: \n"
          "1) Выгрузка по ссылкам\n"
          "2) Выгрузка по файлу")
    task = int(input())
    if task == 1:
        with open('links.txt', 'r') as f:
            links_file = f.readlines()
        for link_file in links_file:
            links_for_parse = get_links_for_1_task(link_file)
            for links_each_page in links_for_parse:
                for i, link in enumerate(links_each_page):
                    html = get_html(link)
                    data = get_data(html, link)
                    write_data_1_task(data, 'result.xlsx')
                    print(i, f"Объект по ссылке {link} записан в файл")

    if task == 2:
        links = get_links("input_file.xlsx")
        for i, link in enumerate(links):
            html = get_html(link)
            data = get_data(html, link)
            print(data)
            write_data_2_task(data, file_path='input_file.xlsx')
            print(i + 1, link, 'обновлена')

    driver.quit()


if __name__ == '__main__':
    main()
