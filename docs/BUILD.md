# 构建与发布

## 电脑端

使用包含 Tkinter 的 Python 3.12（建议）创建虚拟环境，安装 requirements.txt 和 PyInstaller。运行 python launcher.py 可从源码启动。

Windows 打包：

```powershell
python -m pip install -r requirements.txt pyinstaller
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1
```

QuizScanner.spec 从 quizscanner/__init__.py 读取版本号。普通 Python 安装使用 PyInstaller 的 Tkinter 检测；本地存在专用 .python-runtime 时，采用明确的 Tcl/Tk 打包路径。构建缓存与运行时目录不进入 Git。

## 安卓端

需要 JDK 17、Android SDK 36 和 Gradle 9.4.1，设置 JAVA_HOME 和 ANDROID_HOME：

```shell
cd android-app
gradle assembleDebug --no-daemon
```

原发布签名仅保留在维护者本机 signing/classroom.keystore，禁止上传。文件存在时沿用它；文件不存在时 Gradle 使用开发者本机的标准 debug 签名。独立构建的签名可能不同，不能保证覆盖官方发行 APK。正式签名迁移需另行安排。

Gradle/Maven 自动下载 AndroidX、CameraX、OpenCV 和 ZXing 等依赖。原生入口为 NativeActivity，不包含旧 WebView Activity。

## 发布前核对

- 保留 LICENSE 原作者声明、NOTICE 与第三方许可证。
- 不提交学生名单、课堂记录、报告、签名密钥、登录令牌、私有媒体或本机配置。
- 源码进入 Git；EXE、APK、压缩包进入 GitHub Releases，并提供 SHA256SUMS.txt。
- Release 标签必须指向发布源码提交，发行说明注明电脑与安卓两个版本号。
- 将已完成的构建、接口与浏览器检查和未完成的真机验收分别写清。

本版原生 APK 的构建及签名已检查。验证详情见 VERIFICATION.md；不得以编译通过替代真机摄像头和网络验收。
