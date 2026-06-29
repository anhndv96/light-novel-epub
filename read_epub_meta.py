import sys
import zipfile
import xml.etree.ElementTree as ET

def get_epub_metadata(epub_path):
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            # 1. Tìm file .opf từ META-INF/container.xml
            try:
                container_xml = z.read('META-INF/container.xml')
            except KeyError:
                print("Lỗi: Không tìm thấy META-INF/container.xml, file này có thể không phải là chuẩn EPUB.")
                return
                
            root = ET.fromstring(container_xml)
            ns = {'n': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = root.find('.//n:rootfile', ns)
            
            if rootfile is None:
                print("Lỗi: Không tìm thấy khai báo rootfile trong container.xml")
                return
                
            opf_path = rootfile.attrib.get('full-path')
            
            # 2. Đọc file .opf
            opf_content = z.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            # Bóc tách metadata
            metadata = None
            for child in opf_root:
                if child.tag.endswith('metadata'):
                    metadata = child
                    break
                    
            print(f"========== METADATA CỦA FILE: {epub_path} ==========")
            if metadata is not None:
                for elem in metadata:
                    # Bỏ phần namespace trong tag name (ví dụ: {http://purl.org/dc/elements/1.1/}title -> title)
                    tag_name = elem.tag.split('}', 1)[-1]
                    text = elem.text.strip() if elem.text else ""
                    
                    # Trích xuất attribute (ví dụ properties="cover-image")
                    attr_str = ""
                    if elem.attrib:
                        attr_parts = []
                        for k, v in elem.attrib.items():
                            k_clean = k.split('}', 1)[-1]
                            attr_parts.append(f'{k_clean}="{v}"')
                        attr_str = " [" + " ".join(attr_parts) + "]"
                        
                    print(f"<{tag_name}>{attr_str}: {text}")
            else:
                print("Không tìm thấy thẻ <metadata> trong file OPF.")
            print("======================================================")
                
    except Exception as e:
        print(f"Lỗi khi đọc EPUB: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Sử dụng: python read_epub_meta.py <đường_dẫn_tới_file_epub>")
    else:
        get_epub_metadata(sys.argv[1])
