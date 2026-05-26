from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
import zlib
import hashlib
import random
import string
import re
import json
import urllib.parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ObfuscationRequest(BaseModel):
    code: str
    language: str
    level: int
    anti_hooking: bool = False

class ObfuscationResponse(BaseModel):
    obfuscated_code: str
    original_size: int
    obfuscated_size: int
    language: str
    level: int

def generate_random_string(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_variable_name() -> str:
    prefixes = ['_', '__', 'var', 'tmp', 'x', 'y', 'z']
    return random.choice(prefixes) + generate_random_string(random.randint(4, 12))

def encode_base64(data: str) -> str:
    return base64.b64encode(data.encode()).decode()

def decode_base64(data: str) -> str:
    return base64.b64decode(data.encode()).decode()
def compress_data(data: str) -> str:
    compressed = zlib.compress(data.encode())
    return base64.b64encode(compressed).decode()

def decompress_data(data: str) -> str:
    decoded = base64.b64decode(data.encode())
    return zlib.decompress(decoded).decode()

def xor_encrypt(data: str, key: str) -> str:
    encrypted = []
    for i, char in enumerate(data):
        encrypted.append(chr(ord(char) ^ ord(key[i % len(key)])))
    return ''.join(encrypted)

def apply_string_encoding(text: str, level: int) -> str:
    if level >= 3:
        return encode_base64(text)
    elif level >= 2:
        return ''.join([f'\\x{ord(c):02x}' for c in text])
    return text

def obfuscate_python(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        lines = result.split('\n')
        obfuscated_lines = []
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                obfuscated_lines.append(' ' * indent + line.lstrip())
            else:
                obfuscated_lines.append(line)
        result = '\n'.join(obfuscated_lines)
    
    if level >= 2:
        comments = re.findall(r'#.*$', result, re.MULTILINE)
        for comment in comments:
            result = result.replace(comment, '')
    
    if level >= 4:
        strings = re.findall(r'["\']([^"\']*)["\']', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)
                result = result.replace(f'"{s}"', f'__import__("base64").b64decode("{encoded}").decode()')
                result = result.replace(f"'{s}'", f'__import__("base64").b64decode("{encoded}").decode()')
    
    if level >= 6:
        var_map = {}        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*=)', result)
        for var in set(variables):
            if var not in ['True', 'False', 'None', 'if', 'else', 'elif', 'for', 'while', 'def', 'class', 'import', 'from', 'return', 'yield', 'try', 'except', 'finally', 'with', 'as', 'pass', 'break', 'continue', 'lambda', 'and', 'or', 'not', 'in', 'is']:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 8:
        compressed = compress_data(result)
        result = f'exec(__import__("zlib").decompress(__import__("base64").b64decode("{compressed}")).decode())'
    
    if level >= 10:
        key = generate_random_string(16)
        encrypted = xor_encrypt(result, key)
        encoded_encrypted = encode_base64(encrypted)
        result = f'''
_key = "{key}"
_data = __import__("base64").b64decode("{encoded_encrypted}").decode()
_result = []
for i, c in enumerate(_data):
    _result.append(chr(ord(c) ^ ord(_key[i % len(_key)])))
exec(''.join(_result))
'''
    
    if level >= 12:
        layers = level - 11
        for _ in range(layers):
            compressed = compress_data(result)
            result = f'exec(__import__("zlib").decompress(__import__("base64").b64decode("{compressed}")).decode())'
    
    if level >= 14:
        chunks = [result[i:i+50] for i in range(0, len(result), 50)]
        chunk_vars = [generate_variable_name() for _ in chunks]
        declarations = '\n'.join([f'{chunk_vars[i]} = "{chunks[i]}"' for i in range(len(chunks))])
        result = f'{declarations}\nexec({"+".join(chunk_vars)})'
    
    if anti_hooking:
        anti_hook_code = '''
import sys
import inspect

def _anti_hook_check():
    _frame = inspect.currentframe()
    if _frame.f_back and _frame.f_back.f_back:
        _caller = inspect.getframeinfo(_frame.f_back.f_back)
        if 'debug' in _caller.filename.lower() or 'hook' in _caller.filename.lower():
            sys.exit(1)
    del _frame

_anti_hook_check()'''
        result = anti_hook_code + result
    
    return result

def obfuscate_javascript(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'["\']([^"\']*)["\']', result)
        for s in strings:
            if len(s) > 2:
                hex_encoded = ''.join([f'\\x{ord(c):02x}' for c in s])
                result = result.replace(f'"{s}"', f'"{hex_encoded}"')
                result = result.replace(f"'{s}'", f"'{hex_encoded}'")
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b(?=\s*[=;])', result)
        reserved = ['var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'new', 'this', 'typeof', 'instanceof', 'true', 'false', 'null', 'undefined', 'console', 'window', 'document', 'Math', 'Date', 'Array', 'Object', 'String', 'Number', 'Boolean']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = '_' + generate_random_string(8)
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'eval(atob("{encoded}"))'
    
    if level >= 9:
        compressed = compress_data(result)
        result = f'''
(function() {{
    var _d = "{compressed}";
    var _b = atob(_d);
    var _r = [];
    for (var i = 0; i < _b.length; i++) {{
        _r.push(_b.charCodeAt(i));
    }}
    var _i = new Uint8Array(_r);
    var _s = new TextDecoder().decode(pako.inflate(_i));
    eval(_s);
}})();
'''
        if level >= 11:
        key = generate_random_string(16)
        encrypted_chars = [ord(c) ^ ord(key[i % len(key)]) for i, c in enumerate(result)]
        encrypted_array = '[' + ','.join(map(str, encrypted_chars)) + ']'
        result = f'''
(function() {{
    var _k = "{key}";
    var _d = {encrypted_array};
    var _r = "";
    for (var i = 0; i < _d.length; i++) {{
        _r += String.fromCharCode(_d[i] ^ _k.charCodeAt(i % _k.length));
    }}
    eval(_r);
}})();
'''
    
    if level >= 13:
        layers = (level - 12) * 2
        for _ in range(layers):
            encoded = encode_base64(result)
            result = f'eval(atob("{encoded}"))'
    
    if level >= 15:
        chunks = [result[i:i+100] for i in range(0, len(result), 100)]
        chunk_code = 'var _c = [' + ','.join([f'"{c}"' for c in chunks]) + '];'
        result = f'{chunk_code}\neval(_c.join(""));'
    
    if anti_hooking:
        anti_hook_code = '''
(function() {
    var _check = function() {
        if (window._phantom || window.__nightmare || window.callPhantom) {
            window.location.href = 'about:blank';
        }
        if (navigator.webdriver) {
            window.location.href = 'about:blank';
        }
        var _start = new Date();
        debugger;
        var _end = new Date();
        if (_end - _start > 100) {
            window.location.href = 'about:blank';
        }
    };
    setInterval(_check, 1000);
})();
'''
        result = anti_hook_code + result
    
    return result
def obfuscate_html(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'<!--[\s\S]*?-->', '', result)
    
    if level >= 3:
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'>\s+<', '><', result)
    
    if level >= 5:
        tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)', result)
        tag_map = {}
        for tag in set(tags):
            if tag.lower() not in ['html', 'head', 'body', 'script', 'style', 'meta', 'link', 'title']:
                tag_map[tag] = generate_random_string(6)
        for old, new in tag_map.items():
            result = re.sub(f'<{old}', f'<{new}', result, flags=re.IGNORECASE)
            result = re.sub(f'</{old}>', f'</{new}>', result, flags=re.IGNORECASE)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'''<html><body><script>
document.write(atob("{encoded}"));
</script></body></html>'''
    
    if level >= 9:
        script_tags = re.findall(r'<script[^>]*>([\s\S]*?)</script>', result)
        for script in script_tags:
            if script.strip():
                obfuscated_script = obfuscate_javascript(script, level - 8, False)
                result = result.replace(script, obfuscated_script)
    
    if level >= 11:
        compressed = compress_data(result)
        result = f'''<html><body><script>
var _d = "{compressed}";
var _b = atob(_d);
var _r = [];
for (var i = 0; i < _b.length; i++) {{
    _r.push(_b.charCodeAt(i));
}}
var _i = new Uint8Array(_r);
var _s = new TextDecoder().decode(pako.inflate(_i));
document.write(_s);
</script></body></html>'''
    
    if level >= 13:
        chunks = [result[i:i+200] for i in range(0, len(result), 200)]        chunk_script = 'var _h = [' + ','.join([f'"{c}"' for c in chunks]) + '];'
        result = f'''<html><body><script>
{chunk_script}
document.write(_h.join(""));
</script></body></html>'''
    
    if anti_hooking:
        anti_hook_code = '''<script>
(function() {
    if (window._phantom || window.__nightmare || navigator.webdriver) {
        document.body.innerHTML = '';
    }
})();
</script>'''
        result = anti_hook_code + result
    
    return result

def obfuscate_php(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'#.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        result = re.sub(r'\s+', ' ', result)
    
    if level >= 5:
        strings = re.findall(r'["\']([^"\']*)["\']', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)
                result = result.replace(f'"{s}"', f'base64_decode("{encoded}")')
                result = result.replace(f"'{s}'", f'base64_decode("{encoded}")')
    
    if level >= 7:
        var_map = {}
        variables = re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', result)
        reserved = ['_GET', '_POST', '_REQUEST', '_SESSION', '_COOKIE', '_SERVER', '_FILES', '_ENV', 'GLOBALS', 'this']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\$' + old + r'\b', '$' + new, result)
    
    if level >= 9:
        encoded = encode_base64(result)
        result = f'<?php eval(base64_decode("{encoded}")); ?>'    
    if level >= 11:
        compressed = compress_data(result)
        result = f'<?php eval(gzinflate(base64_decode("{compressed}"))); ?>'
    
    if level >= 13:
        key = generate_random_string(16)
        encrypted = xor_encrypt(result, key)
        encoded_encrypted = encode_base64(encrypted)
        result = f'''<?php
$_k = "{key}";
$_d = base64_decode("{encoded_encrypted}");
$_r = "";
for ($i = 0; $i < strlen($_d); $i++) {{
    $_r .= chr(ord($_d[$i]) ^ ord($_k[$i % strlen($_k)]));
}}
eval($_r);
?>'''
    
    if level >= 15:
        layers = level - 14
        for _ in range(layers):
            encoded = encode_base64(result)
            result = f'<?php eval(base64_decode("{encoded}")); ?>'
    
    if anti_hooking:
        anti_hook_code = '''<?php
if (function_exists('xdebug_is_enabled') && xdebug_is_enabled()) {
    exit;
}
if (isset($_SERVER['HTTP_X_DEBUG'])) {
    exit;
}
?>
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_ruby(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'#.*$', '', result, flags=re.MULTILINE)
    
    if level >= 3:
        strings = re.findall(r'["\']([^"\']*)["\']', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)                result = result.replace(f'"{s}"', f'Base64.decode64("{encoded}")')
                result = result.replace(f"'{s}'", f'Base64.decode64("{encoded}")')
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-z_][a-zA-Z0-9_]*)\b(?=\s*=)', result)
        reserved = ['def', 'end', 'class', 'module', 'if', 'else', 'elsif', 'unless', 'while', 'until', 'for', 'do', 'begin', 'rescue', 'ensure', 'return', 'yield', 'break', 'next', 'redo', 'retry', 'true', 'false', 'nil', 'self', 'super', 'require', 'include', 'extend', 'attr_accessor', 'attr_reader', 'attr_writer']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'require "base64"\neval(Base64.decode64("{encoded}"))'
    
    if level >= 9:
        compressed = compress_data(result)
        result = f'''require "base64"
require "zlib"
_d = "{compressed}"
_b = Base64.decode64(_d)
_s = Zlib::Inflate.inflate(_b)
eval(_s)'''
    
    if level >= 11:
        key = generate_random_string(16)
        encrypted = xor_encrypt(result, key)
        encoded_encrypted = encode_base64(encrypted)
        result = f'''require "base64"
_k = "{key}"
_d = Base64.decode64("{encoded_encrypted}")
_r = ""
_d.each_char.with_index do |c, i|
  _r << (c.ord ^ _k[i % _k.length].ord).chr
end
eval(_r)'''
    
    if level >= 13:
        layers = level - 12
        for _ in range(layers):
            encoded = encode_base64(result)
            result = f'require "base64"\neval(Base64.decode64("{encoded}"))'
    
    if anti_hooking:
        anti_hook_code = '''
if defined?(Debugger) || defined?(Byebug) || defined?(Pry)
  exit
end'''
        result = anti_hook_code + result
    
    return result

def obfuscate_java(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                hex_encoded = ''.join([f'\\u{ord(c):04x}' for c in s])
                result = result.replace(f'"{s}"', f'"{hex_encoded}"')
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[=;])', result)
        reserved = ['public', 'private', 'protected', 'static', 'final', 'class', 'interface', 'extends', 'implements', 'new', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'throws', 'import', 'package', 'void', 'int', 'long', 'double', 'float', 'boolean', 'char', 'byte', 'short', 'String', 'Object', 'System', 'out', 'println', 'main']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'''
import java.util.Base64;
String _e = "{encoded}";
String _d = new String(Base64.getDecoder().decode(_e));
// Note: Java cannot eval strings directly, this is a placeholder
'''
    
    if level >= 9:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                char_array = ','.join([str(ord(c)) for c in s])
                result = result.replace(f'"{s}"', f'new String(new int[]{{{char_array}}}, 0, {len(s)}).chars().mapToObj(c -> String.valueOf((char)c)).collect(java.util.stream.Collectors.joining())')
    
    if level >= 11:
        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if level >= 13:        chunks = [result[i:i+100] for i in range(0, len(result), 100)]
        chunk_code = 'String[] _c = {' + ','.join([f'"{c}"' for c in chunks]) + '};'
        result = f'{chunk_code}\nStringBuilder _s = new StringBuilder();\nfor(String _p : _c) _s.append(_p);\n// Use _s.toString()'
    
    if anti_hooking:
        anti_hook_code = '''
if (java.lang.management.ManagementFactory.getRuntimeMXBean().getInputArguments().toString().contains("debug")) {
    System.exit(1);
}
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_csharp(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)
                result = result.replace(f'"{s}"', f'System.Text.Encoding.UTF8.GetString(System.Convert.FromBase64String("{encoded}"))')
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[=;])', result)
        reserved = ['public', 'private', 'protected', 'internal', 'static', 'readonly', 'const', 'class', 'interface', 'struct', 'enum', 'namespace', 'using', 'new', 'return', 'if', 'else', 'for', 'foreach', 'while', 'do', 'switch', 'case', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'void', 'int', 'long', 'double', 'float', 'bool', 'char', 'byte', 'string', 'var', 'this', 'base', 'null', 'true', 'false', 'Console', 'WriteLine', 'Main', 'String', 'Object']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'string _e = "{encoded}";\nstring _d = System.Text.Encoding.UTF8.GetString(System.Convert.FromBase64String(_e));'
    
    if level >= 9:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                char_array = ','.join([f"'{c}'" for c in s])
                result = result.replace(f'"{s}"', f'new string(new char[]{{{char_array}}})')
    
    if level >= 11:        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if level >= 13:
        chunks = [result[i:i+100] for i in range(0, len(result), 100)]
        chunk_code = 'string[] _c = {' + ','.join([f'"{c}"' for c in chunks]) + '};'
        result = f'{chunk_code}\nstring _s = string.Join("", _c);'
    
    if anti_hooking:
        anti_hook_code = '''
if (System.Diagnostics.Debugger.IsAttached) {
    System.Environment.Exit(1);
}
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_cpp(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                hex_encoded = ''.join([f'\\x{ord(c):02x}' for c in s])
                result = result.replace(f'"{s}"', f'"{hex_encoded}"')
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[=;])', result)
        reserved = ['int', 'char', 'float', 'double', 'void', 'bool', 'long', 'short', 'unsigned', 'signed', 'const', 'static', 'class', 'struct', 'enum', 'public', 'private', 'protected', 'virtual', 'override', 'new', 'delete', 'return', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue', 'try', 'catch', 'throw', 'namespace', 'using', 'include', 'define', 'ifdef', 'ifndef', 'endif', 'std', 'cout', 'cin', 'endl', 'string', 'vector', 'map', 'set', 'main']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                char_array = ','.join([f"'\\x{ord(c):02x}'" for c in s])
                result = result.replace(f'"{s}"', f'std::string({{{char_array}}}, {len(s)})')
    
    if level >= 9:        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if level >= 11:
        defines = []
        for i in range(10):
            macro_name = generate_random_string(8)
            macro_value = random.randint(0, 255)
            defines.append(f'#define {macro_name} {macro_value}')
        result = '\n'.join(defines) + '\n' + result
    
    if level >= 13:
        chunks = [result[i:i+100] for i in range(0, len(result), 100)]
        chunk_code = 'const char* _c[] = {' + ','.join([f'"{c}"' for c in chunks]) + '};'
        result = f'{chunk_code}\nstd::string _s;\nfor(int i=0; i<{len(chunks)}; i++) _s += _c[i];'
    
    if anti_hooking:
        anti_hook_code = '''
#ifdef _DEBUG
exit(1);
#endif
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_typescript(code: str, level: int, anti_hooking: bool = False) -> str:
    result = obfuscate_javascript(code, level, anti_hooking)
    
    if level >= 5:
        result = re.sub(r':\s*[a-zA-Z_][a-zA-Z0-9_<>\[\],\s|&]*', '', result)
    
    if level >= 7:
        result = re.sub(r'interface\s+[a-zA-Z_][a-zA-Z0-9_]*\s*{[^}]*}', '', result)
        result = re.sub(r'type\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=[^;]*;', '', result)
    
    return result

def obfuscate_kotlin(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)                result = result.replace(f'"{s}"', f'java.util.Base64.getDecoder().decode("{encoded}").toString(Charsets.UTF_8)')
    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[=:])', result)
        reserved = ['fun', 'val', 'var', 'class', 'interface', 'object', 'when', 'if', 'else', 'for', 'while', 'do', 'return', 'break', 'continue', 'try', 'catch', 'finally', 'throw', 'import', 'package', 'null', 'true', 'false', 'this', 'super', 'is', 'as', 'in', 'out', 'override', 'open', 'abstract', 'final', 'sealed', 'data', 'private', 'protected', 'public', 'internal', 'companion', 'init', 'constructor', 'suspend', 'inline', 'reified', 'typealias', 'String', 'Int', 'Long', 'Double', 'Float', 'Boolean', 'Char', 'Byte', 'Short', 'Unit', 'Any', 'println', 'main']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'val _e = "{encoded}"\nval _d = java.util.Base64.getDecoder().decode(_e).toString(Charsets.UTF_8)'
    
    if level >= 9:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                char_array = ','.join([f"'{c}'" for c in s])
                result = result.replace(f'"{s}"', f'stringOf({char_array})')
    
    if level >= 11:
        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if anti_hooking:
        anti_hook_code = '''
if (java.lang.management.ManagementFactory.getRuntimeMXBean().getInputArguments().toString().contains("debug")) {
    kotlin.system.exitProcess(1)
}
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_swift(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                hex_encoded = ''.join([f'\\u{ord(c):04x}' for c in s])
                result = result.replace(f'"{s}"', f'"{hex_encoded}"')    
    if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[=:])', result)
        reserved = ['var', 'let', 'func', 'class', 'struct', 'enum', 'protocol', 'extension', 'import', 'return', 'if', 'else', 'for', 'while', 'repeat', 'switch', 'case', 'break', 'continue', 'fallthrough', 'do', 'catch', 'throw', 'throws', 'try', 'guard', 'defer', 'in', 'where', 'is', 'as', 'nil', 'true', 'false', 'self', 'Self', 'super', 'init', 'deinit', 'subscript', 'typealias', 'associatedtype', 'static', 'public', 'private', 'fileprivate', 'internal', 'open', 'final', 'lazy', 'weak', 'unowned', 'override', 'mutating', 'nonmutating', 'convenience', 'required', 'optional', 'inout', 'infix', 'prefix', 'postfix', 'operator', 'precedencegroup', 'String', 'Int', 'Double', 'Float', 'Bool', 'Character', 'Array', 'Dictionary', 'Set', 'Optional', 'print', 'main']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'let _e = "{encoded}"\nlet _d = String(data: Data(base64Encoded: _e)!, encoding: .utf8)!'
    
    if level >= 9:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                char_array = ','.join([f'Character(UnicodeScalar({ord(c)})!)' for c in s])
                result = result.replace(f'"{s}"', f'String([{char_array}])')
    
    if level >= 11:
        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if anti_hooking:
        anti_hook_code = '''
#if DEBUG
exit(1)
#endif
'''
        result = anti_hook_code + result
    
    return result

def obfuscate_go(code: str, level: int, anti_hooking: bool = False) -> str:
    result = code
    
    if level >= 1:
        result = re.sub(r'//.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'/\*[\s\S]*?\*/', '', result)
    
    if level >= 3:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 2:
                encoded = encode_base64(s)
                result = result.replace(f'"{s}"', f'string(base64.StdEncoding.DecodeString("{encoded}"))')
        if level >= 5:
        var_map = {}
        variables = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*[:=])', result)
        reserved = ['package', 'import', 'func', 'var', 'const', 'type', 'struct', 'interface', 'map', 'chan', 'go', 'defer', 'return', 'if', 'else', 'for', 'range', 'switch', 'case', 'default', 'break', 'continue', 'fallthrough', 'goto', 'select', 'nil', 'true', 'false', 'iota', 'append', 'cap', 'close', 'complex', 'copy', 'delete', 'imag', 'len', 'make', 'new', 'panic', 'print', 'println', 'real', 'recover', 'string', 'int', 'int8', 'int16', 'int32', 'int64', 'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'float32', 'float64', 'complex64', 'complex128', 'bool', 'byte', 'rune', 'error', 'main', 'fmt', 'Println', 'Sprintf']
        for var in set(variables):
            if var not in reserved:
                var_map[var] = generate_variable_name()
        for old, new in var_map.items():
            result = re.sub(r'\b' + old + r'\b', new, result)
    
    if level >= 7:
        encoded = encode_base64(result)
        result = f'import "encoding/base64"\n_e := "{encoded}"\n_d, _ := base64.StdEncoding.DecodeString(_e)'
    
    if level >= 9:
        strings = re.findall(r'"([^"]*)"', result)
        for s in strings:
            if len(s) > 3:
                byte_array = ','.join([str(ord(c)) for c in s])
                result = result.replace(f'"{s}"', f'string([]byte{{{byte_array}}})')
    
    if level >= 11:
        result = result.replace('\n', '\\n')
        result = result.replace('\t', '\\t')
    
    if anti_hooking:
        anti_hook_code = '''
import "os"
import "runtime/debug"
if debug.ReadBuildInfo() != nil {
    os.Exit(1)
}
'''
        result = anti_hook_code + result
    
    return result

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Advanced Code Obfuscator</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }            h1 { color: #667eea; margin-bottom: 10px; font-size: 2.5em; }
            .subtitle { color: #666; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; }
            select, textarea, input[type="number"] { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; transition: border-color 0.3s; }
            select:focus, textarea:focus, input[type="number"]:focus { outline: none; border-color: #667eea; }
            textarea { min-height: 200px; font-family: 'Courier New', monospace; resize: vertical; }
            button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px 40px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
            button:hover { transform: translateY(-2px); }
            button:active { transform: translateY(0); }
            .result { margin-top: 30px; padding: 20px; background: #f5f5f5; border-radius: 8px; display: none; }
            .result h3 { color: #667eea; margin-bottom: 15px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-value { font-size: 24px; font-weight: bold; color: #667eea; }
            .stat-label { color: #666; font-size: 14px; }
            .code-output { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; white-space: pre-wrap; word-break: break-all; max-height: 400px; overflow-y: auto; }
            .checkbox-group { display: flex; align-items: center; gap: 10px; }
            .checkbox-group input[type="checkbox"] { width: auto; }
            .error { background: #fee; color: #c33; padding: 15px; border-radius: 8px; margin-top: 20px; display: none; }
            .loading { text-align: center; padding: 20px; display: none; }
            .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Advanced Code Obfuscator</h1>
            <p class="subtitle">Protect your code with multi-level obfuscation</p>
            
            <div class="form-group">
                <label for="language">Programming Language</label>
                <select id="language">
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="html">HTML</option>
                    <option value="php">PHP</option>
                    <option value="ruby">Ruby</option>
                    <option value="java">Java</option>
                    <option value="csharp">C#</option>
                    <option value="cpp">C++</option>
                    <option value="typescript">TypeScript</option>
                    <option value="kotlin">Kotlin</option>
                    <option value="swift">Swift</option>
                    <option value="go">Go</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="level">Obfuscation Level (1-15)</label>                <input type="number" id="level" min="1" max="15" value="5">
            </div>
            
            <div class="form-group">
                <label for="code">Source Code</label>
                <textarea id="code" placeholder="Paste your code here..."></textarea>
            </div>
            
            <div class="form-group checkbox-group">
                <input type="checkbox" id="antiHooking">
                <label for="antiHooking">Enable Anti-Hooking Protection (Optional)</label>
            </div>
            
            <button onclick="obfuscateCode()">Obfuscate Code</button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Obfuscating your code...</p>
            </div>
            
            <div class="error" id="error"></div>
            
            <div class="result" id="result">
                <h3>Obfuscation Complete</h3>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value" id="originalSize">0</div>
                        <div class="stat-label">Original Size (bytes)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="obfuscatedSize">0</div>
                        <div class="stat-label">Obfuscated Size (bytes)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="sizeIncrease">0%</div>
                        <div class="stat-label">Size Increase</div>
                    </div>
                </div>
                <div class="code-output" id="codeOutput"></div>
            </div>
        </div>
        
        <script>
            async function obfuscateCode() {
                const code = document.getElementById('code').value;
                const language = document.getElementById('language').value;
                const level = parseInt(document.getElementById('level').value);
                const antiHooking = document.getElementById('antiHooking').checked;
                
                if (!code.trim()) {                    showError('Please enter some code to obfuscate');
                    return;
                }
                
                if (level < 1 || level > 15) {
                    showError('Obfuscation level must be between 1 and 15');
                    return;
                }
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                document.getElementById('error').style.display = 'none';
                
                try {
                    const response = await fetch('/api/obfuscate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code, language, level, anti_hooking: antiHooking })
                    });
                    
                    if (!response.ok) {
                        throw new Error('Obfuscation failed');
                    }
                    
                    const data = await response.json();
                    
                    document.getElementById('originalSize').textContent = data.original_size;
                    document.getElementById('obfuscatedSize').textContent = data.obfuscated_size;
                    const increase = ((data.obfuscated_size - data.original_size) / data.original_size * 100).toFixed(1);
                    document.getElementById('sizeIncrease').textContent = increase + '%';
                    document.getElementById('codeOutput').textContent = data.obfuscated_code;
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    showError(error.message);
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            }
            
            function showError(message) {
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/obfuscate", response_model=ObfuscationResponse)
async def obfuscate_endpoint(request: ObfuscationRequest):
    if request.level < 1 or request.level > 15:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 15")
    
    obfuscators = {
        'python': obfuscate_python,
        'javascript': obfuscate_javascript,
        'html': obfuscate_html,
        'php': obfuscate_php,
        'ruby': obfuscate_ruby,
        'java': obfuscate_java,
        'csharp': obfuscate_csharp,
        'cpp': obfuscate_cpp,
        'typescript': obfuscate_typescript,
        'kotlin': obfuscate_kotlin,
        'swift': obfuscate_swift,
        'go': obfuscate_go,
    }
    
    if request.language not in obfuscators:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")
    
    try:
        obfuscated_code = obfuscators[request.language](request.code, request.level, request.anti_hooking)
        
        return ObfuscationResponse(
            obfuscated_code=obfuscated_code,
            original_size=len(request.code),
            obfuscated_size=len(obfuscated_code),
            language=request.language,
            level=request.level
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Obfuscation error: {str(e)}")

@app.get("/api/languages")
async def get_languages():
    return {
        "languages": [
            {"id": "python", "name": "Python", "max_level": 15},
            {"id": "javascript", "name": "JavaScript", "max_level": 15},
            {"id": "html", "name": "HTML", "max_level": 15},
            {"id": "php", "name": "PHP", "max_level": 15},
            {"id": "ruby", "name": "Ruby", "max_level": 15},
            {"id": "java", "name": "Java", "max_level": 15},
            {"id": "csharp", "name": "C#", "max_level": 15},
            {"id": "cpp", "name": "C++", "max_level": 15},
            {"id": "typescript", "name": "TypeScript", "max_level": 15},
            {"id": "kotlin", "name": "Kotlin", "max_level": 15},
            {"id": "swift", "name": "Swift", "max_level": 15},            {"id": "go", "name": "Go", "max_level": 15},
        ]
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)