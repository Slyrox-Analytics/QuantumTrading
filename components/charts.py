import streamlit.components.v1 as components

def tradingview_widget(symbol="BINANCE:BTCUSDT.P", height=500):

    html = f"""
    <div style="width:100%;">
        <div id="tv_chart" style="width:100%; height:{height}px;"></div>

        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "container_id": "tv_chart",
            "width": "100%",
            "height": {height},
            "symbol": "{symbol}",
            "interval": "5",
            "timezone": "Europe/Berlin",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#020409",
            "enable_publishing": false,
            "allow_symbol_change": false
        }});
        </script>
    </div>
    """

    components.html(html, height=height)
