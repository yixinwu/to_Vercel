#!/usr/bin/env python3
import re
import sys
import quopri

def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_convert.py <input.mhtml>")
        return
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.mhtml', '.html')
    
    try:
        # 以二进制模式读取文件
        with open(input_file, 'rb') as f:
            content = f.read()
        
        # 直接在二进制数据上操作
        # 查找<html>标签
        html_start = content.find(b'<html')
        if html_start == -1:
            print("No <html> tag found")
            # 尝试查找<!DOCTYPE html>
            html_start = content.find(b'<!DOCTYPE html')
            if html_start == -1:
                print("No HTML content found")
                return
        
        # 找到HTML内容的结束（查找</html>标签）
        html_end = content.find(b'</html>', html_start)
        if html_end == -1:
            # 如果找不到结束标签，使用文件末尾
            html_end = len(content)
        else:
            html_end += 7  # 加上</html>的长度
        
        # 提取HTML部分
        html_bytes = content[html_start:html_end]
        
        # 移除软换行
        html_bytes = re.sub(b'=\n', b'', html_bytes)
        
        # 解码quoted-printable编码
        try:
            # 使用quopri解码二进制数据
            decoded_bytes = quopri.decodestring(html_bytes)
            # 尝试用utf-8解码
            html_content = decoded_bytes.decode('utf-8')
            print("Successfully decoded with utf-8")
        except Exception as e:
            print(f"Error decoding with utf-8: {e}")
            # 尝试用gbk解码
            try:
                html_content = decoded_bytes.decode('gbk')
                print("Successfully decoded with gbk")
            except Exception as e:
                print(f"Error decoding with gbk: {e}")
                # 尝试用latin-1解码
                html_content = decoded_bytes.decode('latin-1')
                print("Successfully decoded with latin-1")
        
        # 确保HTML头部有正确的编码声明
        if '<head>' in html_content and 'charset=' not in html_content:
            html_content = html_content.replace('<head>', '<head><meta charset="UTF-8">')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Converted {input_file} to {output_file}")
        print(f"HTML content length: {len(html_content)} characters")
        print(f"First 500 characters: {html_content[:500]}...")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()