#!/usr/bin/env python3
import re
import sys

def convert_mhtml_to_html(mhtml_content):
    # 提取HTML部分
    html_match = re.search(r'Content-Type: text/html.*?\n\n(.*?)------MultipartBoundary', mhtml_content, re.DOTALL)
    if not html_match:
        return ""    
    html_content = html_match.group(1)
    
    # 移除quoted-printable编码
    html_content = re.sub(r'=([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), html_content)
    
    # 移除软换行
    html_content = re.sub(r'=\n', '', html_content)
    
    return html_content

def main():
    if len(sys.argv) != 2:
        print("Usage: python convert_mhtml.py <input.mhtml>")
        return
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.mhtml', '.html')
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            mhtml_content = f.read()
        
        html_content = convert_mhtml_to_html(mhtml_content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Converted {input_file} to {output_file}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()