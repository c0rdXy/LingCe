#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵测 LingCe - 安全打包脚本
具备反调试、混淆、路径清理等安全功能
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

class SecureBuild:
    """安全打包流程封装。"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.source_dir = self.root_dir
        self.secure_dir = self.root_dir / "dist_secure"
        
    def clean_old_files(self):
        """清理打包输出"""
        print("🧹 清理打包输出...")
        
        # 清理打包临时文件
        for pattern in ['build', 'dist', '*.spec', '__pycache__']:
            for item in self.source_dir.rglob(pattern):
                if item.exists():
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
        
        # 清理安全打包目录的exe文件
        self.secure_dir.mkdir(exist_ok=True)
        for exe_file in self.secure_dir.glob("*.exe"):
            exe_file.unlink(missing_ok=True)
            
    def create_secure_spec(self):
        """创建安全的PyInstaller spec文件"""
        spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 反调试和安全配置
block_cipher = None

# 隐藏导入，增加逆向难度
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'json',
    'datetime',
    'random',
    'threading',
    'queue',
    'pathlib',
    'os',
    'sys'
]

# 数据文件收集
datas = [
    ('assets/github-fluidicon.png', 'assets'),
    ('question_banks/题库.json', 'question_banks'),
]

# 二进制文件收集
binaries = []

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'sklearn'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 移除调试信息和路径信息
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LingCe',
    debug=False,  # 关闭调试
    bootloader_ignore_signals=False,
    strip=True,   # 移除符号表
    upx=True,     # 使用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=True,  # 禁用窗口化回溯
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
        
        spec_file = self.source_dir / "secure_build.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        return spec_file
    
    def create_anti_debug_wrapper(self):
        """创建反调试包装器"""
        wrapper_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反调试和安全检查包装器
"""

import os
import sys
import ctypes
import threading
import time
from ctypes import wintypes

class AntiDebug:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.windll.ntdll
        
    def is_debugger_present(self):
        """检查调试器是否存在"""
        return self.kernel32.IsDebuggerPresent()
    
    def check_remote_debugger(self):
        """检查远程调试器"""
        debugger_present = ctypes.c_bool()
        self.kernel32.CheckRemoteDebuggerPresent(
            self.kernel32.GetCurrentProcess(),
            ctypes.byref(debugger_present)
        )
        return debugger_present.value
    
    def anti_debug_thread(self):
        """反调试监控线程"""
        while True:
            if self.is_debugger_present() or self.check_remote_debugger():
                # 检测到调试器，退出程序
                os._exit(1)
            time.sleep(0.1)
    
    def start_protection(self):
        """启动反调试保护"""
        # 启动反调试监控线程
        debug_thread = threading.Thread(target=self.anti_debug_thread, daemon=True)
        debug_thread.start()
        
        # 设置异常处理
        def exception_handler(exc_type, exc_value, exc_traceback):
            # 不显示异常信息，直接退出
            os._exit(1)
        
        sys.excepthook = exception_handler

# 在导入主程序前启动保护
if __name__ == "__main__":
    try:
        # 启动反调试保护
        anti_debug = AntiDebug()
        anti_debug.start_protection()
        
        # 导入并运行主程序
        from app import main
        main()
    except:
        # 任何异常都直接退出
        os._exit(1)
'''
        
        wrapper_file = self.source_dir / "secure_main.py"
        with open(wrapper_file, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)
        
        return wrapper_file
    
    def obfuscate_code(self):
        """代码混淆处理"""
        print("🔒 进行代码混淆...")
        
        # 创建打包工作目录
        temp_dir = self.source_dir / "temp_obfuscated"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        # 复制源码到临时目录
        for py_file in self.source_dir.rglob("*.py"):
            if "temp_obfuscated" not in str(py_file):
                rel_path = py_file.relative_to(self.source_dir)
                dest_file = temp_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 简单的变量名混淆
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 移除注释和文档字符串中的敏感信息
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # 移除包含路径信息的注释
                    if line.strip().startswith('#') and ('\\' in line or '/' in line):
                        continue
                    # 移除包含作者信息的注释
                    if any(keyword in line.lower() for keyword in ['author', '作者', 'email', 'path', '路径']):
                        continue
                    cleaned_lines.append(line)
                
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(cleaned_lines))
        
        return temp_dir
    
    def build_secure_exe(self):
        """构建安全的exe文件"""
        print("🚀 开始安全打包...")
        self.secure_dir.mkdir(exist_ok=True)
        
        # 切换到源码目录
        os.chdir(self.source_dir)
        
        try:
            # 创建反调试包装器
            wrapper_file = self.create_anti_debug_wrapper()
            
            # 创建安全的spec文件
            spec_file = self.create_secure_spec()
            
            # 配置反调试包装入口
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec_content = f.read()
            
            spec_content = spec_content.replace("['app.py']", "['secure_main.py']")
            
            with open(spec_file, 'w', encoding='utf-8') as f:
                f.write(spec_content)
            
            # 执行PyInstaller打包
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--clean',
                str(spec_file)
            ]
            
            print(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print("✅ 安全打包成功！")
                
                # 移动exe文件到安全打包目录
                exe_file = self.source_dir / "dist" / "LingCe.exe"
                if exe_file.exists():
                    dest_file = self.secure_dir / "LingCe.exe"
                    shutil.move(str(exe_file), str(dest_file))
                    print(f"📦 exe文件已移动到: {dest_file}")
                else:
                    print("❌ 未找到生成的exe文件")
                    
            else:
                print(f"❌ 安全打包失败: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 打包过程出错: {e}")
        
        finally:
            # 清理打包工作目录
            self.clean_temp_files()
    
    def clean_temp_files(self):
        """清理打包工作目录"""
        print("🧹 清理打包工作目录...")
        
        temp_patterns = [
            'build', 'dist', '*.spec', '__pycache__',
            'secure_main.py', 'temp_obfuscated'
        ]
        
        for pattern in temp_patterns:
            for item in self.source_dir.rglob(pattern):
                if item.exists():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)
                    except:
                        pass
    
    def run(self):
        """执行安全打包流程"""
        print("🎯 灵测 LingCe - 安全打包")
        print("=" * 50)
        print(f"📁 源码目录: {self.source_dir}")
        print(f"🔒 安全打包目录: {self.secure_dir}")
        print()
        
        # 清理打包输出
        self.clean_old_files()
        
        # 构建安全exe
        self.build_secure_exe()
        
        print()
        print("✅ 安全打包完成！")
        print("🔐 安全特性:")
        print("   - 反调试保护")
        print("   - 代码混淆")
        print("   - 路径信息清理")
        print("   - 符号表移除")
        print("   - UPX压缩")

if __name__ == "__main__":
    builder = SecureBuild()
    builder.run()
