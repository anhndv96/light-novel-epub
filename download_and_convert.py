import sys
import os
import subprocess
import glob
import time
import base64

try:
    from bs4 import BeautifulSoup
    from ebooklib import epub
except ImportError:
    print("Missing required libraries. Installing 'beautifulsoup4' and 'EbookLib'...")
    subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4", "EbookLib"], check=True)
    # Import again after installation
    from bs4 import BeautifulSoup
    from ebooklib import epub

def download_novel(url):
    print(f"Downloading from {url}...")
    # Use npx to run pixiv-novel-dl
    out_dir = "downloads"
    os.makedirs(out_dir, exist_ok=True)
    
    # We clear the downloads directory to easily find the new file
    for f in glob.glob(os.path.join(out_dir, "*.html")):
        os.remove(f)
        
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx_cmd, "pixiv-novel-dl", url, "-o", out_dir, "--no-convert-webp"]
    try:
        # Run command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error downloading novel:")
        print(e.stderr)
        sys.exit(1)
        
    # Find the downloaded html file
    html_files = glob.glob(os.path.join(out_dir, "*.html"))
    if not html_files:
        print("No HTML file found after download.")
        sys.exit(1)
        
    return html_files[0]

def convert_html_to_epub(html_file, url, series_name, chapter_index):
    print(f"Converting {html_file} to EPUB...")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove head completely
    head = soup.find('head')
    if head:
        head.decompose()
        
    title = "Unknown Title"
    
    # Extract footer data
    footer = soup.find('footer')
    meta_dict = {}
    if footer:
        for strong in footer.find_all('strong'):
            k = strong.get_text(strip=True).rstrip(':')
            v_parts = []
            for sibling in strong.next_siblings:
                if sibling.name in ['br', 'strong']:
                    break
                if isinstance(sibling, str):
                    v_parts.append(sibling.strip())
                else:
                    v_parts.append(sibling.get_text(strip=True))
            v = " ".join(v_parts).strip()
            if k and v:
                meta_dict[k] = v
                
        # Fallback
        if not meta_dict:
            for p in footer.find_all(['p', 'div', 'span', 'li']):
                text = p.get_text(strip=True)
                if ':' in text:
                    k, v = text.split(':', 1)
                    meta_dict[k.strip()] = v.strip()
            if not meta_dict:
                for text in footer.stripped_strings:
                    if ':' in text:
                        k, v = text.split(':', 1)
                        meta_dict[k.strip()] = v.strip()
        footer.decompose()

    # Extract header description and title
    header = soup.find('header')
    description = ""
    if header:
        h1_tag = header.find('h1')
        if h1_tag:
            title = h1_tag.get_text(strip=True)
        desc_tag = header.find('p', class_='description')
        if desc_tag:
            description = desc_tag.get_text(strip=True)
            desc_tag.decompose()
    else:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text
        else:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.text

    import re
    title = re.sub(r'^(R\s+|\[R-18\]\s+|\[R-18G\]\s+)', '', title)
    title = re.sub(r'\s*-\s*pixiv.*$', '', title)
    title = title.strip()

    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(title)
    book.set_language('vi')
    
    # Helper function to find keys case-insensitively
    def get_meta_val(keys):
        for k, v in meta_dict.items():
            k_lower = k.lower()
            if any(key in k_lower for key in keys):
                return v
        return None

    tags_val = get_meta_val(['tags', 'tag']) or ""
    writer_val = get_meta_val(['author', 'writer']) or ""
    date_val = get_meta_val(['date']) or ""
    
    if description:
        book.add_metadata('DC', 'description', description)
        
    if writer_val:
        book.add_metadata('DC', 'creator', writer_val)
        
    if date_val:
        book.add_metadata('DC', 'date', date_val)
        
    book.add_metadata('DC', 'identifier', f"url:{url}")
    
    if tags_val:
        for t in tags_val.split(','):
            if t.strip():
                book.add_metadata('DC', 'subject', t.strip())
                
    book.add_metadata('DC', 'subject', 'Hentai')
    
    # Series metadata for Kavita (Calibre standard)
    book.add_metadata(None, 'meta', '', {'name': 'calibre:series', 'content': series_name})
    book.add_metadata(None, 'meta', '', {'name': 'calibre:series_index', 'content': str(chapter_index)})
    
    # Extract cover image (first image after description)
    first_img = soup.find('img')
    if first_img:
        src = first_img.get('src')
        if src and src.startswith('data:image/'):
            try:
                header_b64, b64data = src.split(',', 1)
                img_format = header_b64.split(';')[0].split('/')[1]
                img_data = base64.b64decode(b64data)
                book.set_cover(f"cover.{img_format}", img_data)
                first_img.decompose()
            except Exception as e:
                print(f"Failed to process cover image: {e}")
                
    # Create chapters
    chapter = epub.EpubHtml(title=title, file_name='chap_01.xhtml', lang='en')
    
    # Process remaining images
    img_count = 1
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and src.startswith('data:image/'):
            try:
                header_b64, b64data = src.split(',', 1)
                img_format = header_b64.split(';')[0].split('/')[1]
                img_data = base64.b64decode(b64data)
                
                img_filename = f"image_{img_count}.{img_format}"
                epub_img = epub.EpubItem(uid=f"image_{img_count}", file_name=img_filename, media_type=f"image/{img_format}", content=img_data)
                book.add_item(epub_img)
                
                img['src'] = img_filename
                img_count += 1
            except Exception as e:
                print(f"Failed to process image: {e}")
            
    for script in soup(["script", "style"]):
        script.decompose()
        
    for a in soup.find_all('a'):
        a.unwrap()
        
    body = soup.find('body')
    if body:
        chapter.content = body.decode_contents()
    else:
        chapter.content = soup.decode_contents()
        
    book.add_item(chapter)
    book.spine = [chapter]
        
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    epub_filename = os.path.join(os.path.dirname(html_file), f"{safe_title}.epub")
    epub.write_epub(epub_filename, book, {})
    print(f"Successfully created: {epub_filename}")
    
    try:
        os.remove(html_file)
        print(f"Deleted original HTML file: {html_file}")
    except OSError as e:
        print(f"Error deleting {html_file}: {e}")
    
def main():
    if len(sys.argv) < 4:
        print("Usage: python download_and_convert.py <pixiv_url> <series_name> <chapter_index>")
        sys.exit(1)
        
    url = sys.argv[1]
    series_name = sys.argv[2]
    chapter_index = sys.argv[3]
    
    html_file = download_novel(url)
    convert_html_to_epub(html_file, url, series_name, chapter_index)

if __name__ == "__main__":
    main()
