# pywin32 (IFileOpenDialog) でのフォルダ複数選択の実装方法

## 目的
Windows 10/11 環境において、Python (`pywin32`) を使用して**ネイティブなフォルダ選択ダイアログ**を表示し、ユーザーに**複数のフォルダを一括選択**させたい。

## 現状の問題
`IFileOpenDialog` インターフェースを使用し、オプションとして `FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT` を設定しても、ダイアログ上で複数のフォルダを選択（ハイライト）することができない。単一選択の挙動になってしまう。

## コードスニペット (抜粋)
```python
import pythoncom
from win32com.shell import shell, shellcon

def ask_multiple_folders():
    try:
        pythoncom.CoInitialize()
        dialog = pythoncom.CoCreateInstance(
            shell.CLSID_FileOpenDialog,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IFileOpenDialog
        )
        
        # フラグ設定
        # FOS_PICKFOLDERS (0x20) : フォルダ選択モード
        # FOS_ALLOWMULTISELECT (0x200) : 複数選択許可
        options = dialog.GetOptions()
        options |= shellcon.FOS_PICKFOLDERS | shellcon.FOS_ALLOWMULTISELECT
        dialog.SetOptions(options)
        
        dialog.Show(None)
        
        # 結果取得 (GetResults)
        results = dialog.GetResults()
        # ...
    finally:
        pythoncom.CoUninitialize()
```

## 質問
1. `FOS_PICKFOLDERS` と `FOS_ALLOWMULTISELECT` は本当に共存できないのか？
2. VBA の `msoFileDialogFolderPicker` + `AllowMultiSelect` のように、ネイティブダイアログでフォルダ複数選択を実現するための正しいフラグ設定や回避策はあるか？
3. `IFileOpenDialog` ではなく、より古い `SHBrowseForFolder` や別の API を使うべきか？（ただしモダンな UI が望ましい）

正しい実装方法、または `pywin32` での動作確認済みコードを提示してください。