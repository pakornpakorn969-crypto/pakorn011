WebView myWebView = (WebView) findViewById(R.id.webview);
myWebView.getSettings().setJavaScriptEnabled(true);
myWebView.loadUrl("http://192.168.1.50:8000"); // ใส่ IP เครื่องเซิร์ฟเวอร์