import json
from collections import deque

def build_search_indexes(crawled_data):
    """Membangun indeks yang diperlukan dari data crawling."""
    url_index = {entry['url']: entry for entry in crawled_data}
    parent_map = {entry['url']: entry['parent'] for entry in crawled_data}

    adjacency_list = {}
    for entry in crawled_data:
        parent = entry.get('parent')
        if parent:
            if parent not in adjacency_list:
                adjacency_list[parent] = []
            adjacency_list[parent].append(entry['url'])
    return url_index, parent_map, adjacency_list


def get_seed_url(crawled_data):
    """Mencari seed URL dari data crawling (biasanya yang tidak punya parent)."""
    for entry in crawled_data:
        if not entry.get('parent'):
            return entry['url']
    return None


def depth_limited_search(keyword, crawled_data, max_depth=2): # Tambahkan crawled_data
    """Depth-limited BFS search"""
    url_index, parent_map, adjacency_list = build_search_indexes(crawled_data)
    start_url = get_seed_url(crawled_data)
    
    if not start_url:
        print("No seed URL found in the provided data!")
        return []
    
    results = []
    visited = set()
    queue = deque([(start_url, 0)])
    keyword_lower = keyword.lower()
    
    print(f"[BFS-DLS] Starting search from: {start_url} with max_depth={max_depth}")
    
    while queue:
        current_url, depth = queue.popleft()
        
        if current_url in visited or depth > max_depth:
            continue
        visited.add(current_url)
        
        entry = url_index.get(current_url)
        if not entry:
            continue
            
        title = entry.get('title', '').lower()
        content = entry.get('content', '').lower()
        
        score = 0
        if keyword_lower in title:
            score += 1.0
        if keyword_lower in content:
            score += 0.8
            
        if score > 0:
            depth_multiplier = 1.0 - (depth * 0.1)
            if depth_multiplier < 0.1:
                depth_multiplier = 0.1
            total_score = score * depth_multiplier
            
            results.append((entry, total_score))
            print(f"[BFS-DLS] Found match (depth {depth}): {entry.get('title', 'No Title')}")
        
        children = adjacency_list.get(current_url, [])
        for child_url in children:
            if child_url not in visited:
                queue.append((child_url, depth + 1))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def dfs_limited_search(keyword, crawled_data, max_depth=2): # Tambahkan crawled_data
    """Depth-limited DFS search"""
    url_index, parent_map, adjacency_list = build_search_indexes(crawled_data)
    start_url = get_seed_url(crawled_data)
    
    if not start_url:
        print("No seed URL found in the provided data!")
        return []
    
    results = []
    visited = set()
    stack = [(start_url, 0)]
    keyword_lower = keyword.lower()
    
    print(f"[DFS-DLS] Starting search from: {start_url} with max_depth={max_depth}")

    while stack:
        current_url, depth = stack.pop()
        
        if current_url in visited or depth > max_depth:
            continue
        visited.add(current_url)
        
        entry = url_index.get(current_url)
        if not entry:
            continue
        
        title = entry.get('title', '').lower()
        content = entry.get('content', '').lower()
        
        score = 0
        if keyword_lower in title:
            score += 1.0
        if keyword_lower in content:
            score += 0.8
            
        if score > 0:
            depth_multiplier = 1.0 - (depth * 0.1)
            if depth_multiplier < 0.1:
                depth_multiplier = 0.1
            total_score = score * depth_multiplier
            
            results.append((entry, total_score))
            print(f"[DFS-DLS] Found match (depth {depth}): {entry.get('title', 'No Title')}")
        
        children = adjacency_list.get(current_url, [])
        for child_url in reversed(children): 
            if child_url not in visited:
                stack.append((child_url, depth + 1))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def reconstruct_path(target_url, crawled_data): # Tambahkan crawled_data
    """Reconstruct route from seed to target using parent mapping."""
    url_index, parent_map, _ = build_search_indexes(crawled_data)
    path = []
    current = target_url
    while current:
        entry = url_index.get(current, {'title': 'Unknown', 'url': current})
        path.append((entry.get('title', 'No Title'), entry['url']))
        current = parent_map.get(current)
    return list(reversed(path))

# Hapus bagian CLI yang sudah kita hapus sebelumnya
# (Jika Anda memiliki bagian CLI di bawah __name__ == '__main__', itu perlu dihapus)