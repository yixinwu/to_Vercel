#!/usr/bin/env python3
import re
import sys

def convert_mhtml_to_html(mhtml_content):
    # 提取HTML部分，使用更灵活的方式
    # 查找Content-Type: text/html部分，然后提取直到下一个边界标记
    html_start = mhtml_content.find('Content-Type: text/html')
    if html_start == -1:
        return ""
    
    # 找到HTML内容的开始（空行之后）
    html_content_start = mhtml_content.find('\n\n', html_start)
    if html_content_start == -1:
        return ""
    html_content_start += 2
    
    # 使用固定的边界标记（从文件中提取）
    boundary_marker = "------MultipartBoundary--EboKL7gPwuGSpHR0w5V3adg0ZWw3t33uqEQaJFa3JG----"
    
    # 找到HTML内容的结束
    html_content_end = mhtml_content.find(boundary_marker, html_content_start)
    if html_content_end == -1:
        # 如果找不到边界标记，尝试使用另一种方式提取
        # 查找HTML的结束标签
        html_end_tags = ['</html>', '</HTML>']
        for end_tag in html_end_tags:
            end_pos = mhtml_content.find(end_tag, html_content_start)
            if end_pos != -1:
                html_content_end = end_pos + len(end_tag)
                break
        else:
            # 如果还是找不到，返回前100000字符作为内容
            html_content = mhtml_content[html_content_start:html_content_start + 100000]
            # 移除quoted-printable编码
            html_content = re.sub(r'=([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), html_content)
            # 移除软换行
            html_content = re.sub(r'=\n', '', html_content)
            # 确保HTML头部有正确的编码声明
            if '<head>' in html_content and 'charset=' not in html_content:
                html_content = html_content.replace('<head>', '<head><meta charset="UTF-8">')
            return html_content
    
    html_content = mhtml_content[html_content_start:html_content_end]
    
    # 移除quoted-printable编码
    html_content = re.sub(r'=([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), html_content)
    
    # 移除软换行
    html_content = re.sub(r'=\n', '', html_content)
    
    # 确保HTML头部有正确的编码声明
    if '<head>' in html_content and 'charset=' not in html_content:
        html_content = html_content.replace('<head>', '<head><meta charset="UTF-8">')
    
    return html_content

def main():
    if len(sys.argv) != 2:
        print("Usage: python convert_mhtml.py <input.mhtml>")
        return
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.mhtml', '.html')
    
    try:
        # 以二进制模式读取文件，避免编码问题
        with open(input_file, 'rb') as f:
            mhtml_content = f.read().decode('utf-8', errors='ignore')
        
        html_content = convert_mhtml_to_html(mhtml_content)
        
        if not html_content:
            print("No HTML content found in the MHTML file")
            return
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Converted {input_file} to {output_file}")
        print(f"HTML content length: {len(html_content)} characters")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()