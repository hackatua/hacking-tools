#!/usr/bin/env python3

from urllib.request import urlopen, Request
from urllib.error import HTTPError
from queue import Queue
from typing import List
from re import search
import sys
from threading import Thread
from argparse import ArgumentParser, RawDescriptionHelpFormatter

AGENT = "Mozilla/5.0 (X11: Lunux x86_64: rv:19.0) Gecko/20100101 Firefox/19.0"
DEFAULT_THREADS = 10

def http_get(url: str):
    request = Request(url, headers={
        'User-Agent': AGENT
    })
    try:
        with urlopen(request) as response:
            data = response.read()
            return {
                "data": data,
                "status": response.status,
                "url": response.url
            }
    except HTTPError as error:
        return {
            "status": error.code,
        }
        
def get_dictionary(remote_dictionary_url: str) -> List[str]:
    response = http_get(remote_dictionary_url)
    data = response["data"]
    return data.decode("UTF-8").split("\n")

def has_extension(word: str) -> bool:
    return search("(\.\w+)$", word)

def get_dirs(remote_dictionary_url: str, extensions: List[str]) -> Queue:
    print(f"[+] Retrieving wordlist from {remote_dictionary_url} ...")
    dictionary = get_dictionary(remote_dictionary_url)
    print(f"[+] Loaded {len(dictionary)} words from {remote_dictionary_url}")
    print(f"[+] Building dictionary with extensions {extensions} ...")
    words = Queue()

    for raw_word in dictionary:
        word = raw_word.strip()
        if len(word) == 0 or word.startswith("#"):
            continue

        words.put(word)
        if not has_extension(word) and len(extensions):
            for extension in extensions:
                words.put(f"{word}.{extension}")

    print(f"[+] The final dictionary has approximately {words.qsize()} words")
    return words

def dir_test_handler(target_url: str, words: Queue):
    while not words.empty():
        url = f"{target_url}/{words.get()}"
        print(f"[+] {words.qsize()} dirs left" + " " * 10, end='\r')

        try:
            response = http_get(url)
        except:
            continue

        status = response["status"]
        if status >= 200 and status < 300:
            final_url = response["url"]
            if url == final_url:
                print(f"  [*] [{status}]: {url}")
            else:
                print(f"  [*] [{status}]: {url} -> {final_url}")
        elif status == 401 or status == 403:
            print(f"  [!] [{status}]: {url}")
        elif status >= 400 and status < 600:
            continue
        else:
            print(f"  [?] [{status}]: {url}")

def parse_arguments():
    example_text = "\n".join([
        "usage:",
        "  python3 %(prog)s -u http://10.0.0.103 -d https://..../directory-list-2.3-medium.txt -e html,txt -t 20",
        "  python3 %(prog)s -t -u http://10.0.0.103 -d https://.../directory-list-2.3-medium.txt"
    ])
    parser = ArgumentParser(
        description="HTTP directory lister program that retrieves the wordlist through HTTP and only uses default Python libraries",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=example_text
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        help="Target URL (-u http://10.0.0.103)",
        required=True
    )
    parser.add_argument(
        "-d" ,"--dict",
        type=str,
        help="Dictionary URL (-d -d https://.../directory-list-2.3-medium.txt)",
        required=True
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        help="Number of threads (-t 20)",
        default=DEFAULT_THREADS,
        required=False
    )
    parser.add_argument(
        "-e", "--ext",
        type=str,
        help="File extensions to test, separated by \",\" (-e html,txt)",
        default="",
        required=False
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    dirs = get_dirs(args.dict, args.ext.split(","))
    print(f"[+] Ready to do directory discovery on {args.url}")
    print("[+] Press enter to continue")
    sys.stdin.readline()
    print(f"[+] Spawning {args.threads} threads...")
    for _ in range(DEFAULT_THREADS):
        thread = Thread(
            target=dir_test_handler,
            args=(args.url, dirs, )
        )
        thread.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[!] Exiting...")
        sys.exit(0)