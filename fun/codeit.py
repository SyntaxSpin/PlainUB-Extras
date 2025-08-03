import os
import html
import asyncio
import uuid
from pyrogram.types import Message, ReplyParameters

from app import BOT, bot

TEMP_DIR = "temp_codeit/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8

LANGUAGES = {
    "python": ("Python", "py"), "py": ("Python", "py"),
    "java": ("Java", "java"),
    "c++": ("C++", "cpp"), "cpp": ("C++", "cpp"),
    "javascript": ("JavaScript", "js"), "js": ("JavaScript", "js"),
    "c#": ("C#", "cs"), "cs": ("C#", "cs"),
    "html": ("HTML", "html"),
    "kotlin": ("Kotlin", "kt"), "kt": ("Kotlin", "kt"),
    "assembly": ("Assembly", "asm"), "asm": ("Assembly", "asm"),
    "go": ("Go", "go"), "golang": ("Go", "go"),
    "rust": ("Rust", "rs"), "rs": ("Rust", "rs"),
    "swift": ("Swift", "swift"),
    "ruby": ("Ruby", "rb"), "rb": ("Ruby", "rb"),
    "php": ("PHP", "php"),
    "c": ("C", "c"),
    "brainfuck": ("Brainfuck", "bf"), "bf": ("Brainfuck", "bf"),
    "lolcode": ("LOLCODE", "lol"), "lol": ("LOLCODE", "lol"),
    "r": ("R", "r"),
    "julia": ("Julia", "jl"), "jl": ("Julia", "jl"),
    "matlab": ("MATLAB", "m"),
    "sql": ("SQL", "sql"),
    "plpgsql": ("PL/pgSQL", "sql"),
    "tsql": ("T-SQL", "sql"),
    "mql": ("MQL", "js"),
    "vhdl": ("VHDL", "vhd"),
    "verilog": ("Verilog", "v"),
    "bash": ("Bash", "sh"), "shell": ("Bash", "sh"), "sh": ("Bash", "sh"),
    "powershell": ("PowerShell", "ps1"), "ps1": ("PowerShell", "ps1"),
    "perl": ("Perl", "pl"), "pl": ("Perl", "pl"),
    "scss": ("SCSS", "scss"),
    "sass": ("SASS", "sass"),
    "less": ("LESS", "less"),
    "graphql": ("GraphQL", "graphql"), "gql": ("GraphQL", "graphql"),
    "haskell": ("Haskell", "hs"), "hs": ("Haskell", "hs"),
    "erlang": ("Erlang", "erl"), "erl": ("Erlang", "erl"),
    "elixir": ("Elixir", "ex"), "ex": ("Elixir", "ex"),
    "ocaml": ("OCaml", "ml"), "ml": ("OCaml", "ml"),
    "lisp": ("Lisp", "lisp"),
    "scheme": ("Scheme", "scm"), "scm": ("Scheme", "scm"),
    "clojure": ("Clojure", "clj"), "clj": ("Clojure", "clj"),
    "prolog": ("Prolog", "pro"), "pro": ("Prolog", "pro"),
    "f#": ("F#", "fs"), "fs": ("F#", "fs"),
    "ada": ("Ada", "adb"),
    "cobol": ("COBOL", "cbl"), "cbl": ("COBOL", "cbl"),
    "fortran": ("Fortran", "f90"),
    "latex": ("LaTeX", "tex"), "tex": ("LaTeX", "tex"),
    "regex": ("Regex", "txt"),
    "solidity": ("Solidity", "sol"), "sol": ("Solidity", "sol"),
    "q#": ("Q#", "qs"), "qs": ("Q#", "qs"),
    "scratch": ("Scratch", "sb3"),
    "gdscript": ("GDScript", "gd"), "gd": ("GDScript", "gd"),
    "dart": ("Dart", "dart"),
}

def text_to_brainfuck(text: str) -> str:
    brainfuck_code = []
    memory = [0]
    pointer = 0
    
    for char in text:
        target_value = ord(char)
        current_value = memory[pointer]
        diff = target_value - current_value
        simple_way = ('+' * diff if diff > 0 else '-' * abs(diff))
        loop_way = ""

        if abs(diff) > 10:
            factor = int(target_value**0.5)
            if factor > 1:
                remaining = target_value - (factor * factor)
                loop_code = f">{'+'*factor}[<{''.join(['+']*factor)}>-]<"
                if remaining > 0:
                    loop_code += '+' * remaining
                else:
                    loop_code += '-' * abs(remaining)
                if len(loop_code) < len(simple_way):
                    loop_way = loop_code

        if loop_way and not current_value:
             brainfuck_code.append(loop_way)
        else:
            brainfuck_code.append(simple_way)

        brainfuck_code.append('.')
        memory[pointer] = target_value
    return "".join(brainfuck_code)

def generate_code(language: str, text: str) -> str:
    """Generates a 'Hello, World!'-style program for the given language and text."""

    if language == "Brainfuck":
        return text_to_brainfuck(text)

    escaped_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    code_templates = {
        "Python": f'print("{escaped_text}")',
        "Java": f'public class Main {{\n    public static void main(String[] args) {{\n        System.out.println("{escaped_text}");\n    }}\n}}',
        "C++": f'#include <iostream>\n\nint main() {{\n    std::cout << "{escaped_text}";\n    return 0;\n}}',
        "JavaScript": f'console.log("{escaped_text}");',
        "C#": f'using System;\n\nclass Program {{\n    static void Main(string[] args) {{\n        Console.WriteLine("{escaped_text}");\n    }}\n}}',
        "HTML": f'<!DOCTYPE html>\n<html>\n<head><title>Message</title></head>\n<body>\n    <p>{html.escape(text)}</p>\n</body>\n</html>',
        "Kotlin": f'fun main() {{\n    println("{escaped_text}")\n}}',
        "Assembly": (
            'section .data\n'
            f'    msg db "{escaped_text}", 0\n\n'
            'section .text\n'
            '    global _start\n\n'
            '_start:\n'
            '    ; This is a simplified representation for Linux x86-64 NASM syntax.\n'
            '    ; It does not calculate string length dynamically.\n'
            '    mov rax, 1 ; syscall for write\n'
            '    mov rdi, 1 ; file descriptor (stdout)\n'
            '    mov rsi, msg ; message to write\n'
            '    mov rdx, 14 ; placeholder length\n'
            '    syscall\n\n'
            '    mov rax, 60 ; syscall for exit\n'
            '    xor rdi, rdi ; exit code 0\n'
            '    syscall'
        ),
        "Go": f'package main\n\nimport "fmt"\n\nfunc main() {{\n    fmt.Println("{escaped_text}")\n}}',
        "Rust": f'fn main() {{\n    println!("{escaped_text}");\n}}',
        "Swift": f'print("{escaped_text}")',
        "Ruby": f'puts "{escaped_text}"',
        "PHP": f'<?php\n\necho "{escaped_text}";\n',
        "C": f'#include <stdio.h>\n\nint main() {{\n    printf("{escaped_text}");\n    return 0;\n}}',
        "LOLCODE": (
            'HAI 1.2\n'
            f'VISIBLE "{text}"\n'
            'KTHXBYE'
        ),
        "R": f'print("{escaped_text}")',
        "Julia": f'println("{escaped_text}")',
        "MATLAB": f'disp("{text.replace("\"", "\"\"")}");',
        "SQL": f"SELECT '{text.replace(\"'\", \"''\")}';",
        "PL/pgSQL": f"DO $$\nBEGIN\n  RAISE NOTICE '{text.replace(\"'\", \"''\")}';\nEND $$;",
        "T-SQL": f"PRINT '{text.replace(\"'\", \"''\")}';",
        "MQL": f'db.collection.insertOne({{ message: "{escaped_text}" }});',
        "VHDL": f'-- VHDL does not have a standard way to print to console.\n-- This is a conceptual representation.\n-- Message: {text}',
        "Verilog": f'module hello_world;\n  initial begin\n    $display("{escaped_text}");\n    $finish;\n  end\nendmodule',
        "Bash": f'echo "{escaped_text}"',
        "PowerShell": f'Write-Host "{escaped_text}"',
        "Perl": f'print "{escaped_text}\\n";',
        "SCSS": f'/* Message: {text} */\n\n.message::before {{\n  content: "{escaped_text}";\n}}',
        "SASS": f'/* Message: {text} */\n\n.message:before\n  content: "{escaped_text}"',
        "LESS": f'/* Message: {text} */\n\n.message:before {{\n  content: "{escaped_text}";\n}}',
        "GraphQL": f'# GraphQL is a query language, not for printing text.\n# This is a conceptual representation.\n\nquery GetMessage {{\n  message(text: "{escaped_text}")\n}}',
        "Haskell": f'main :: IO ()\nmain = putStrLn "{escaped_text}"',
        "Erlang": f'-module(hello).\n-export([start/0]).\n\nstart() ->\n    io:fwrite("{escaped_text}\\n").',
        "Elixir": f'IO.puts "{escaped_text}"',
        "OCaml": f'print_endline "{escaped_text}"',
        "Lisp": f'(format t "{escaped_text}~%")',
        "Scheme": f'(display "{escaped_text}")\n(newline)',
        "Clojure": f'(println "{escaped_text}")',
        "Prolog": f':- initialization(main).\nmain :- write("{text.replace("\"", "\"\"")}"), nl, halt.',
        "F#": f'printfn "{escaped_text}"',
        "Ada": f'with Ada.Text_IO; use Ada.Text_IO;\nprocedure Hello is\nbegin\n    Put_Line ("{text}");\nend Hello;',
        "COBOL": f'IDENTIFICATION DIVISION.\nPROGRAM-ID. HELLO.\nPROCEDURE DIVISION.\n    DISPLAY "{text}".\n    STOP RUN.',
        "Fortran": f'program hello\n    print *, "{text.replace("\"", "\"\"")}"\nend program hello',
        "LaTeX": f'\\documentclass{{article}}\n\\begin{{document}}\n{text}\n\\end{{document}}',
        "Regex": f'^{re.escape(text)}$',
        "Solidity": f'// Solidity contracts do not print to console.\n// This is a conceptual representation.\ncontract Message {{\n    string public constant message = "{escaped_text}";\n}}',
        "Q#": f'namespace Quantum.Hello {{\n    open Microsoft.Quantum.Canon;\n    open Microsoft.Quantum.Intrinsic;\n\n    operation SayHello() : Unit {{\n        Message("{escaped_text}");\n    }}\n}}',
        "Scratch": '// Scratch is a visual language. This text would be in a "say" block.',
        "GDScript": f'extends SceneTree\n\nfunc _init():\n    print("{escaped_text}")\n    quit()',
        "Dart": f'void main() {{\n  print("{escaped_text}");\n}}',
    }
    return code_templates.get(language, f"// Language '{language}' not supported.")

def sync_save_code_to_file(code_string: str, file_ext: str) -> str:
    unique_id = str(uuid.uuid4())
    output_path = os.path.join(TEMP_DIR, f"main_{unique_id}.{file_ext}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code_string)
    return output_path

def safe_escape(text: str) -> str:
    return html.escape(str(text))

@bot.add_cmd(cmd="codeit")
async def codeit_handler(bot: BOT, message: Message):
    """
    CMD: CODEIT
    INFO: Turns a text message into a program file with a code preview.
    USAGE:
        .codeit [lang] (text)
        .codeit [lang] (in reply to a message)
    LANGUAGES: python, java, c++, js, cs, html, kotlin, asm, go, rust, swift, ruby, php, c, bf, lol
    """
    replied_msg = message.replied
    
    if not message.input:
        return await message.reply("<b>Usage:</b> .codeit <language> [text]", del_in=ERROR_VISIBLE_DURATION)

    parts = message.input.split(maxsplit=1)
    lang_alias = parts[0].lower()
    
    if lang_alias not in LANGUAGES:
        return await message.reply(f"Unsupported language: <code>{lang_alias}</code>.", del_in=ERROR_VISIBLE_DURATION)

    lang_name, file_ext = LANGUAGES[lang_alias]
    
    text_to_code = ""
    if len(parts) > 1:
        text_to_code = parts[1]
    elif replied_msg and replied_msg.text:
        text_to_code = replied_msg.text
    else:
        return await message.reply("Please provide text or reply to a text message.", del_in=ERROR_VISIBLE_DURATION)

    progress_message = await message.reply("<code>Generating code...</code>")
    
    output_path = ""
    temp_files = []
    try:
        code_output = generate_code(lang_name, text_to_code)
        
        output_path = await asyncio.to_thread(sync_save_code_to_file, code_output, file_ext)
        temp_files.append(output_path)
        
        preview_code = safe_escape(code_output)
        caption = f'<pre class="language-{lang_alias}">{preview_code}</pre>'
        
        if len(caption) > 1024:
            overhead_len = len(f'<pre class="language-{lang_alias}"></pre>\n... (truncated)')
            max_code_len = 1024 - overhead_len
            truncated_code = safe_escape(code_output[:max_code_len])
            caption = f'<pre class="language-{lang_alias}">{truncated_code}\n... (truncated)</pre>'
        
        reply_target = replied_msg or message
        await bot.send_document(
            chat_id=message.chat.id,
            document=output_path,
            caption=caption,
            reply_parameters=ReplyParameters(message_id=reply_target.id)
        )
        
        await progress_message.delete()
        await message.delete()

    except Exception as e:
        error_text = f"<b>Error:</b> Could not generate code.\n<code>{html.escape(str(e))}</code>"
        await progress_message.edit(error_text, del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f):
                os.remove(f)
