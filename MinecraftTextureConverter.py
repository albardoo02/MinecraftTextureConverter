import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import json
import shutil
import threading
import time

# =================================================================================
# 対応表
# =================================================================================
PATH_RENAME_MAP = {
    "textures/entity/zombie_pigman.png": "textures/entity/zombie/zombified_piglin.png",
    "textures/painting/paintings_kristoffer_zetterstrand.png": "textures/entity/painting/kristoffer_zetterstrand.png",
    "textures/gui/widgets.png": "textures/gui/sprites/widget/widgets.png",
    "block/zombie_pigman": "entity/zombie/zombified_piglin",
    "painting/paintings_kristoffer_zetterstrand": "entity/painting/kristoffer_zetterstrand",
    "gui/widgets": "gui/sprites/widget/widgets",
}

# =================================================================================
# バックエンド処理 (実際の変換ロジック)
# =================================================================================

def update_pack_mcmeta(pack_folder, target_format, log_callback):
    meta_path = os.path.join(pack_folder, 'pack.mcmeta')
    if not os.path.exists(meta_path):
        log_callback("エラー: pack.mcmeta が見つかりません。")
        return False
    try:
        with open(meta_path, 'r', encoding='utf-8') as f: data = json.load(f)
        original_format = data.get('pack', {}).get('pack_format', '不明')
        log_callback(f"pack.mcmetaを更新中... (旧: {original_format} -> 新: {target_format})")
        if 'pack' not in data: data['pack'] = {}
        data['pack']['pack_format'] = target_format
        with open(meta_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
        return True
    except Exception as e:
        log_callback(f"pack.mcmetaの更新中にエラー: {e}")
        return False

def rename_files_and_folders(source_folder, output_folder, log_callback):
    """対応表を元に画像ファイルをリネームし、新しい場所へコピーする"""
    source_assets = os.path.join(source_folder, 'assets', 'minecraft')
    output_assets = os.path.join(output_folder, 'assets', 'minecraft')
    if not os.path.exists(source_assets):
        log_callback("assets/minecraftフォルダが見つかりません。リネームをスキップ。")
        return
    rename_count = 0
    png_rename_map = {k: v for k, v in PATH_RENAME_MAP.items() if k.endswith('.png')}
    for old_partial, new_partial in png_rename_map.items():
        old_full = os.path.join(source_assets, *old_partial.split('/'))
        new_full = os.path.join(output_assets, *new_partial.split('/'))
        if os.path.exists(old_full):
            try:
                os.makedirs(os.path.dirname(new_full), exist_ok=True)
                shutil.copy2(old_full, new_full) # moveではなくcopy
                log_callback(f"リネームコピー: {os.path.basename(old_full)} -> {new_partial}")
                rename_count += 1
            except Exception as e:
                log_callback(f"エラー: {os.path.basename(old_full)} のリネームコピー中: {e}")
    log_callback(f"合計 {rename_count} 個のバニラファイルをリネームコピーしました。")

def move_and_log_unknown_files(source_assets_dir, target_assets_dir, log_callback):
    log_callback("独自ファイルのチェックとコピーを開始...")
    moved_count = 0
    if not os.path.isdir(source_assets_dir):
        log_callback("エラー: コピー元のassetsフォルダが見つかりません。")
        return
    for dirpath, _, filenames in os.walk(source_assets_dir):
        for filename in filenames:
            source_file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(source_file_path, source_assets_dir)
            is_managed = any(relative_path.replace(os.sep, '/') == old_path for old_path in PATH_RENAME_MAP.keys() if old_path.endswith('.png'))
            if not is_managed:
                target_file_path = os.path.join(target_assets_dir, relative_path)
                try:
                    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                    shutil.copy2(source_file_path, target_file_path)
                    log_callback(f"コピー: {relative_path.replace(os.sep, '/')}")
                    moved_count += 1
                except Exception as e:
                    log_callback(f"独自ファイルコピーエラー: {filename} - {e}")
    log_callback(f"合計 {moved_count} 個の独自ファイルをコピーしました。")

def update_json_files(pack_folder, log_callback):
    """JSONファイル内のテクスチャパスを更新し、各ファイルのチェックをログに出力する"""
    assets_folder = os.path.join(pack_folder, 'assets', 'minecraft')
    update_count = 0
    checked_count = 0
    log_callback("JSONファイルのパスを更新中...")
    
    json_files_to_process = []
    for folder in ['models', 'blockstates']:
        target_dir = os.path.join(assets_folder, folder)
        if not os.path.isdir(target_dir): continue
        for dirpath, _, filenames in os.walk(target_dir):
            for filename in filenames:
                if filename.endswith('.json'):
                    json_files_to_process.append(os.path.join(dirpath, filename))

    for file_path in json_files_to_process:
        relative_path = os.path.relpath(file_path, assets_folder).replace(os.sep, '/')
        log_callback(f"チェック中: {relative_path}")
        checked_count += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            original_content = content
            for old, new in PATH_RENAME_MAP.items():
                content = content.replace(f'"{old.replace(".png", "")}"', f'"{new.replace(".png", "")}"')
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
                update_count += 1
        except Exception as e:
            log_callback(f"  -> エラー: {relative_path} の処理中: {e}")
    log_callback(f"合計 {checked_count} 個のJSONファイルをチェックし、{update_count} 個を更新しました。")

def supplement_with_vanilla(pack_folder, vanilla_assets_folder, log_callback):
    log_callback("バニラテクスチャでの補完を開始...")
    pack_assets = os.path.join(pack_folder, 'assets')
    vanilla_assets = vanilla_assets_folder
    copy_count = 0
    for dirpath, _, filenames in os.walk(vanilla_assets):
        for filename in filenames:
            vanilla_file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(vanilla_file_path, vanilla_assets)
            pack_file_path = os.path.join(pack_assets, relative_path)
            if not os.path.exists(pack_file_path):
                try:
                    os.makedirs(os.path.dirname(pack_file_path), exist_ok=True)
                    shutil.copy2(vanilla_file_path, pack_file_path)
                    copy_count += 1
                except Exception as e:
                    log_callback(f"コピーエラー: {filename} - {e}")
    log_callback(f"合計 {copy_count} 個の不足ファイルをバニラテクスチャで補完しました。")

def create_zip_archive(source_folder, target_version_str, log_callback):
    try:
        folder_name = os.path.basename(source_folder)
        if folder_name.endswith("_converted"):
            folder_name = folder_name[:-10]
        zip_name = f"{folder_name}_{target_version_str.split(' ')[0]}"
        output_path = os.path.join(os.path.dirname(source_folder), zip_name)
        log_callback(f"ZIPファイルを作成中: {zip_name}.zip")
        shutil.make_archive(output_path, 'zip', source_folder)
        log_callback(f"ZIP化完了: {output_path}.zip")
        return True
    except Exception as e:
        log_callback(f"ZIP化中にエラーが発生しました: {e}")
        return False

# =================================================================================
# GUIアプリケーション本体
# =================================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft Texture Converter v7 (ログ強化版)")
        self.geometry("700x650")
        ctk.set_appearance_mode("System")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        # (GUIのレイアウト部分は変更なし)
        pack_frame=ctk.CTkFrame(self); pack_frame.grid(row=0,column=0,padx=10,pady=5,sticky="ew"); pack_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pack_frame,text="変換元パック:").grid(row=0,column=0,padx=10,pady=5); self.pack_path_var=ctk.StringVar(); self.pack_entry=ctk.CTkEntry(pack_frame,textvariable=self.pack_path_var); self.pack_entry.grid(row=0,column=1,padx=10,pady=5,sticky="ew")
        ctk.CTkButton(pack_frame,text="参照...",command=lambda: self.browse_folder(self.pack_path_var,"変換元フォルダを選択")).grid(row=0,column=2,padx=10,pady=5)
        output_frame=ctk.CTkFrame(self); output_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew"); output_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(output_frame,text="出力先フォルダ:").grid(row=0,column=0,padx=10,pady=5); self.output_path_var=ctk.StringVar(); self.output_entry=ctk.CTkEntry(output_frame,textvariable=self.output_path_var); self.output_entry.grid(row=0,column=1,padx=10,pady=5,sticky="ew")
        ctk.CTkButton(output_frame,text="参照...",command=lambda: self.browse_folder(self.output_path_var,"出力先フォルダを選択")).grid(row=0,column=2,padx=10,pady=5)
        vanilla_frame=ctk.CTkFrame(self); vanilla_frame.grid(row=2,column=0,padx=10,pady=5,sticky="ew"); vanilla_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(vanilla_frame,text="バニラassets:").grid(row=0,column=0,padx=10,pady=5); self.vanilla_path_var=ctk.StringVar(); self.vanilla_entry=ctk.CTkEntry(vanilla_frame,textvariable=self.vanilla_path_var); self.vanilla_entry.grid(row=0,column=1,padx=10,pady=5,sticky="ew")
        ctk.CTkButton(vanilla_frame,text="参照...",command=lambda: self.browse_folder(self.vanilla_path_var,"バニラのassetsフォルダを選択")).grid(row=0,column=2,padx=10,pady=5)
        option_frame=ctk.CTkFrame(self); option_frame.grid(row=3,column=0,padx=10,pady=5,sticky="ew"); option_frame.grid_columnconfigure(1, weight=1)
        self.version_map={"1.20.3-1.20.4 (22)": 22, "1.20.2 (18)": 18, "1.20/1.20.1 (15)": 15, "1.19.4 (13)": 13, "1.19.3 (12)": 12, "1.19-1.19.2 (9)": 9}
        ctk.CTkLabel(option_frame, text="変換先バージョン:").grid(row=0, column=0, padx=10, pady=5); self.version_menu=ctk.CTkOptionMenu(option_frame, values=list(self.version_map.keys())); self.version_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        action_frame=ctk.CTkFrame(self); action_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        self.supplement_var=ctk.BooleanVar(value=True); ctk.CTkCheckBox(action_frame,text="バニラで補完",variable=self.supplement_var).pack(side="left",padx=10)
        self.zip_var=ctk.BooleanVar(value=True); ctk.CTkCheckBox(action_frame,text="完了後にZIP化",variable=self.zip_var).pack(side="left",padx=10)
        self.convert_button=ctk.CTkButton(action_frame,text="変換開始",command=self.start_conversion_thread); self.convert_button.pack(side="right",padx=10)
        self.log_textbox=ctk.CTkTextbox(self); self.log_textbox.grid(row=5,column=0,padx=10,pady=10,sticky="nsew")

    def log(self,message): self.log_textbox.insert("end",f"[{time.strftime('%H:%M:%S')}] {message}\n"); self.log_textbox.see("end")
    def browse_folder(self,var,title): folder=filedialog.askdirectory(title=title); var.set(folder); self.log(f"{title}: {folder}")
    
    def conversion_logic(self):
        try:
            source_folder = self.pack_path_var.get()
            output_folder_base = self.output_path_var.get()
            vanilla_folder = self.vanilla_path_var.get()
            if not os.path.isdir(source_folder): self.log("エラー: 変換元パックのフォルダを正しく選択してください。"); return
            if not os.path.isdir(output_folder_base): self.log("エラー: 出力先フォルダを正しく選択してください。"); return
            
            source_folder_name = os.path.basename(source_folder)
            output_folder = os.path.join(output_folder_base, f"{source_folder_name}_converted")
            self.log(f"出力先: {output_folder}")
            if os.path.exists(output_folder):
                if not messagebox.askyesno("確認", f"出力先フォルダ '{output_folder}' は既に存在します。\n上書きしますか？"):
                    self.log("処理を中断しました。"); return
                shutil.rmtree(output_folder)
            os.makedirs(output_folder)

            selected_version_str = self.version_menu.get()
            target_format = self.version_map[selected_version_str]
            self.log(f"\n--- 変換開始 (ターゲット: {selected_version_str}) ---")

            # --- ★ 新しい処理の流れ ---
            # 1. pack.mcmetaをコピーして更新
            source_mcmeta = os.path.join(source_folder, 'pack.mcmeta')
            target_mcmeta = os.path.join(output_folder, 'pack.mcmeta')
            if os.path.exists(source_mcmeta):
                shutil.copy2(source_mcmeta, target_mcmeta)
                update_pack_mcmeta(output_folder, target_format, self.log)
            else:
                self.log("エラー: pack.mcmetaが見つかりません。"); return

            # 2. バニラファイルをリネームコピー
            rename_files_and_folders(source_folder, output_folder, self.log)

            # 3. 独自ファイルをコピー＆ログ表示
            source_assets_dir = os.path.join(source_folder, 'assets')
            target_assets_dir = os.path.join(output_folder, 'assets')
            move_and_log_unknown_files(source_assets_dir, target_assets_dir, self.log)

            # 4. JSONを更新
            update_json_files(output_folder, self.log)
            
            # 5. バニラで補完 & ZIP化
            if self.supplement_var.get():
                if not os.path.isdir(vanilla_folder) or os.path.basename(vanilla_folder) != 'assets': 
                    self.log("エラー: バニラassetsフォルダを正しく選択してください。補完をスキップします。")
                else:
                    supplement_with_vanilla(output_folder, vanilla_folder, self.log)
            if self.zip_var.get():
                create_zip_archive(output_folder, selected_version_str, self.log)
            
            self.log("--- 処理完了 ---"); messagebox.showinfo("完了","変換処理が完了しました。")
        except Exception as e:
            self.log(f"致命的なエラーが発生しました: {e}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
        finally:
            self.convert_button.configure(state="normal")

    def start_conversion_thread(self): self.convert_button.configure(state="disabled"); threading.Thread(target=self.conversion_logic).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()