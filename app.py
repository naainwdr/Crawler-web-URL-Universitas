from flask import Flask, render_template, request, jsonify
import json
import os
import sys
import hashlib
from urllib.parse import urlparse

# --- PERUBAHAN DI SINI UNTUK IMPOR DARI SUBFOLDER ---
# Tambahkan path ke folder 'crawler' dan 'search' ke sys.path
# Ini agar Python bisa menemukan modul di dalam subfolder tersebut
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'search'))
# --- AKHIR PERUBAHAN IMPOR ---

# Import fungsi-fungsi dari route_search.py (sekarang berada di folder 'search')
from route_search import depth_limited_search, dfs_limited_search, reconstruct_path

# Import bfs_crawler (sekarang berada di folder 'crawler')
from bfs_crawler import bfs_crawl_ui

app = Flask(__name__)

# Direktori untuk menyimpan data yang di-cache
CACHE_DIR = "data"
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache in-memory untuk data yang sering diakses (opsional, tapi bagus untuk performa)
_crawled_data_cache = {}

# --- FUNGSI NORMALISASI URL BARU ---
def normalize_url_for_cache(url):
    """
    Menormalisasi URL untuk tujuan caching agar 'www.' dan trailing slash konsisten.
    Misal:
    https://www.ui.ac.id/ -> https://ui.ac.id
    https://ui.ac.id/ -> https://ui.ac.id
    ui.ac.id -> https://ui.ac.id (jika scheme tidak ada, default ke https)
    """
    parsed_url = urlparse(url)

    # Tambahkan skema default jika tidak ada (misal: 'ui.ac.id' menjadi 'https://ui.ac.id')
    scheme = parsed_url.scheme if parsed_url.scheme else "https"
    netloc = parsed_url.netloc

    # Hapus 'www.' jika ada di netloc
    if netloc.startswith("www."):
        netloc = netloc[4:] # Hapus 'www.'

    # Gabungkan kembali tanpa query/fragment untuk hash
    # Hanya gunakan scheme, netloc, dan path, lalu hapus trailing slash dari path
    path = parsed_url.path.rstrip('/') if parsed_url.path else ''
    
    normalized_base_url = f"{scheme}://{netloc}{path}"
    
    return normalized_base_url

def get_cache_filename(seed_url):
    """Membuat nama file cache berdasarkan hash MD5 dari URL yang sudah dinormalisasi."""
    normalized_url = normalize_url_for_cache(seed_url)
    seed_hash = hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
    return f"crawled_data_{seed_hash}.json"

def load_or_crawl_data(seed_url):
    """
    Memuat data dari cache jika ada, jika tidak, lakukan crawling.
    Mengembalikan data yang di-cache dan path file.
    """
    if not seed_url:
        return [], None

    # Normalisasi URL yang dimasukkan pengguna SEBELUM hashing dan pemrosesan lebih lanjut
    # Pastikan URL memiliki skema, jika tidak, tambahkan 'https'
    if not urlparse(seed_url).scheme:
        seed_url = "https://" + seed_url
        
    normalized_seed_url = normalize_url_for_cache(seed_url)
    seed_hash = hashlib.md5(normalized_seed_url.encode('utf-8')).hexdigest()
    
    # Periksa cache in-memory
    if seed_hash in _crawled_data_cache:
        print(f"[CACHE] Data for {normalized_seed_url} found in in-memory cache.")
        return _crawled_data_cache[seed_hash], os.path.join(CACHE_DIR, get_cache_filename(seed_url))

    cache_filename = get_cache_filename(seed_url)
    cache_filepath = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_filepath):
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _crawled_data_cache[seed_hash] = data # Tambahkan ke in-memory cache
                print(f"[INFO] Loaded {len(data)} entries from file cache: {cache_filepath}")
                return data, cache_filepath
        except Exception as e:
            print(f"[ERROR] Error loading cached data from {cache_filepath}: {e}")
            # Hapus file cache yang rusak jika terjadi error
            os.remove(cache_filepath)
            print(f"[INFO] Removed corrupted cache file: {cache_filepath}")
            # Lanjutkan untuk crawling baru
    
    # Jika tidak ada di cache, lakukan crawling
    print(f"[INFO] No cache found for {normalized_seed_url}. Starting new crawl.")
    try:
        # Panggil bfs_crawl_ui dengan URL yang sudah dinormalisasi dan nama file output yang spesifik
        crawled_file_path = bfs_crawl_ui(seed_url=normalized_seed_url, max_depth=2, output_filename=cache_filename)
        if crawled_file_path:
            with open(crawled_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _crawled_data_cache[seed_hash] = data # Tambahkan ke in-memory cache
                return data, crawled_file_path
        else:
            return [], None
    except Exception as e:
        print(f"[ERROR] Crawling failed for {normalized_seed_url}: {e}")
        return [], None


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form.get('keyword', '').strip()
    search_method = request.form.get('search_method', 'depth_limited_bfs')
    seed_url_input = request.form.get('seed_url', '').strip()

    if not keyword:
        return jsonify({'keyword': '', 'results': [], 'seed_url': seed_url_input})
    
    if not seed_url_input:
        return jsonify({'keyword': keyword, 'results': [], 'seed_url': seed_url_input, 'error': 'Seed URL cannot be empty.'})

    print(f"[DEBUG] Searching for keyword: '{keyword}' on seed: '{seed_url_input}' using method: '{search_method}'")
    
    # Muat atau lakukan crawling data untuk seed_url yang diberikan
    crawled_data, _ = load_or_crawl_data(seed_url_input)

    if not crawled_data:
        return jsonify({
            'keyword': keyword,
            'results': [],
            'seed_url': seed_url_input,
            'error': 'Failed to load or crawl data for the provided URL. Please check the URL and try again.'
        })

    # Pilih fungsi pencarian berdasarkan search_method dan teruskan data yang sudah dimuat
    if search_method == 'dfs_limited':
        results_raw = dfs_limited_search(keyword, crawled_data, max_depth=2)
    else: # Default ke BFS DLS
        results_raw = depth_limited_search(keyword, crawled_data, max_depth=2)

    results = []
    for entry, score in results_raw:
        results.append({
            'entry': entry,
            'score': score
        })
    
    print(f"[DEBUG] Found {len(results)} results")
    
    return jsonify({
        'keyword': keyword,
        'results': results,
        'seed_url': seed_url_input
    })

@app.route('/route')
def route():
    target_url = request.args.get('url', '')
    seed_url_for_route = request.args.get('seed_url', '') # Ambil seed_url dari query string

    if not target_url or not seed_url_for_route:
        return "URL atau Seed URL tidak ditemukan untuk membuat rute.", 400

    # Muat data spesifik untuk seed_url yang relevan dengan target_url ini
    crawled_data_for_route, _ = load_or_crawl_data(seed_url_for_route)

    if not crawled_data_for_route:
        return "Data crawling tidak ditemukan untuk seed URL yang diberikan. Tidak dapat membuat rute.", 404

    # Panggil reconstruct_path dengan data yang relevan
    path = reconstruct_path(target_url, crawled_data_for_route)
    
    return render_template('route.html', path=path)

@app.route('/debug')
def debug():
    # Contoh bagaimana kita bisa mengakses data dari cache in-memory atau file
    # Untuk debug, kita bisa menampilkan beberapa data dari cache default UI jika ada
    ui_seed_data, _ = load_or_crawl_data("https://www.ui.ac.id/") # Tetap pakai www untuk testing
    return jsonify({
        'total_cached_seeds': len(os.listdir(CACHE_DIR)),
        'in_memory_cache_size': len(_crawled_data_cache),
        'sample_ui_entries': ui_seed_data[:3] if ui_seed_data else [],
        'all_titles_ui_sample': [item.get('title', 'No Title') for item in ui_seed_data[:10]] if ui_seed_data else []
    })

if __name__ == '__main__':
    app.run(debug=True)