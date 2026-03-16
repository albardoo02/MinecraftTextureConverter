インストールパッケージ
```
pip install customtkinter
pip install pyinstaller
```

アイコンなし
- `pyinstaller --onefile --windowed --name MinecraftTextureConverter MinecraftTextureConverter.py`


アイコンあり
- `pyinstaller --onefile --windowed --name MinecraftTextureConverter --icon=icon.ico MinecraftTextureConverter.py`


2026/3/16追記
- 適当に作って放置しているやつなので、実用性は知りません。
- テクスチャの構造自体も頻繁に変わるので、この変換システムが使えるかどうかは保証できません。
