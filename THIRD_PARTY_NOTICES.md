# 第三方依赖与许可证

QuizScanner 项目本身遵循 MIT；以下依赖采用各自的许可条款。

| 依赖 | 用途 | 许可证或出处 |
|---|---|---|
| KaTeX | 电脑网页数学公式 | MIT；保留 vendor/katex/LICENSE，另复制至 THIRD_PARTY_LICENSES |
| CPython | Windows 程序运行时 | Python Software Foundation 等许可，见 CPython-LICENSE.txt |
| NumPy | 数值与图像处理 | BSD 及所包含组件的许可证，保留安装包的完整许可证目录 |
| Pillow | 答题卡、PDF 与图像 | 保留 Pillow 安装包许可证 |
| OpenCV / opencv-contrib-python | 卡片识别 | Apache 2.0 及第三方组件许可，保留 LICENSE 和 LICENSE-3RD-PARTY |
| PyInstaller | Windows 打包 | GPL 与引导程序许可例外，见安装包 COPYING.txt |
| AndroidX、Compose、Material 3、CameraX | 原生安卓界面与相机 | Apache 2.0，见各组件上游源码许可 |
| OpenCV Android 4.12.0 | 手机本地 ArUco 识别 | Apache 2.0，https://github.com/opencv/opencv/blob/4.12.0/LICENSE |
| ZXing 3.5.3 | 连接二维码识别 | Apache 2.0，https://github.com/zxing/zxing/blob/zxing-3.5.3/LICENSE |
| Kotlin 与 kotlinx.coroutines | 安卓语言与协程 | Apache 2.0，见各组件上游源码许可 |

THIRD_PARTY_LICENSES 记录本次 Windows 构建所使用的依赖许可证。安卓依赖通过 Gradle/Maven 声明下载，不将依赖库源码或本机缓存当作本项目原创代码。二进制发行随附第三方许可证压缩包。
