from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import undetected_chromedriver as uc
import json
import time
import os
import hashlib

def bfs_crawl_ui(seed_url="https://www.ui.ac.id/", max_depth=2, output_filename=None):
    visited = set()
    queue = deque()
    results = []

    domain = urlparse(seed_url).netloc
    queue.append((seed_url, None, 0))

    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    # options.add_argument("--headless") # Komen/hapus baris ini SEMENTARA untuk melihat browser
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(60) # Tingkatkan timeout page load

    print(f"[START] Crawling from: {seed_url}")
    while queue:
        current_url, parent_url, depth = queue.popleft()

        if current_url in visited or depth > max_depth:
            continue
        visited.add(current_url)

        try:
            print(f"[INFO] Visiting (depth {depth}): {current_url}")
            driver.get(current_url)
            time.sleep(5) # Beri waktu lebih banyak untuk halaman dimuat sebelum interaksi

            # --- PENANGANAN POP-UP (Alert JS & Tombol OK) ---
            # Coba tangani alert JS (upi.edu says)
            max_alert_attempts = 5 # Coba lebih banyak kali
            for attempt in range(max_alert_attempts):
                try:
                    alert = WebDriverWait(driver, 5).until(EC.alert_is_present()) # Tunggu alert muncul
                    alert_text = alert.text
                    alert.accept()
                    print(f"[INFO] JS Alert ditutup (Percobaan {attempt + 1}): '{alert_text}'")
                    time.sleep(2) # Beri waktu setelah menutup alert
                except TimeoutException:
                    # Tidak ada alert yang muncul dalam waktu tunggu, keluar dari loop
                    break
                except NoAlertPresentException: # Sudah tidak ada alert, keluar dari loop
                    break
                except Exception as alert_e:
                    print(f"[WARNING] Gagal menutup alert pada percobaan {attempt + 1} for {current_url}: {alert_e}")
                    break # Keluar jika ada error lain saat menutup alert

            # Coba tangani tombol OK kustom (jika ada)
            try:
                # Tunggu hingga tombol OK muncul dan bisa diklik
                ok_button = WebDriverWait(driver, 10).until( # Tingkatkan waktu tunggu untuk tombol OK
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'OK')]"))
                )
                ok_button.click()
                print("[INFO] Tombol OK diklik.")
                time.sleep(3) # Beri waktu setelah klik tombol
            except (TimeoutException, NoSuchElementException):
                pass # Tombol OK tidak ditemukan atau tidak bisa diklik

            # Tambahkan waktu tunggu eksplisit setelah semua interaksi awal
            time.sleep(2) 
            
            # Sekarang ambil sumber halaman setelah semua interaksi
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'No Title'
            text = soup.get_text(separator=' ', strip=True)

            results.append({
                'url': current_url,
                'title': title,
                'content': text,
                'parent': parent_url,
                'depth': depth
            })

            for link in soup.find_all('a', href=True):
                href = urljoin(current_url, link['href'])
                parsed_href = urlparse(href)

                if domain in parsed_href.netloc and href not in visited:
                    queue.append((href, current_url, depth + 1))

        except WebDriverException as wd_e:
            print(f"[ERROR] WebDriver Error accessing {current_url}: {wd_e}")
            # Tangani error spesifik WebDriver (misal, crash browser, koneksi terputus)
            # Jika ini terjadi berulang, mungkin perlu restart driver atau lewati URL ini
            continue
        except Exception as e:
            print(f"[ERROR] General Error accessing {current_url}: {e}")
            continue

    driver.quit()

    os.makedirs("data", exist_ok=True)
    
    if output_filename is None:
        seed_hash = hashlib.md5(seed_url.encode('utf-8')).hexdigest()
        output_filename = f"crawled_data_{seed_hash}.json"
    
    file_path = os.path.join("data", output_filename)
    # Hanya simpan hasil jika ada data yang berhasil di-crawl
    if results:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[DONE] Total halaman disimpan ke {file_path}: {len(results)}")
    else:
        print(f"[WARNING] Tidak ada halaman yang berhasil di-crawl untuk {seed_url}. Tidak ada file cache yang dibuat.")
        # Jika file cache 0 entries sebelumnya ada, kita mungkin ingin menghapusnya untuk memaksa retry
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[WARNING] Menghapus file cache kosong/rusak: {file_path}")

    return file_path if results else None # Mengembalikan None jika tidak ada hasil