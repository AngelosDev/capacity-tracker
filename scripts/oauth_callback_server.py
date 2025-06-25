from flask import Flask, request

app = Flask(__name__)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if code:
        return f"""
            <html>
                <head>
                    <title>OAuth Callback</title>
                    <style>
                        body {{
                            font-family: sans-serif;
                            font-size: 14px;
                        }}
                        .copyable {{
                            background-color: #f4f4f4;
                            padding: 5px;
                            border: 1px solid #ddd;
                            border-radius: 3px;
                            display: inline-block;
                            cursor: pointer;
                            width: 300px;
                            word-wrap: break-word;
                            white-space: pre-wrap;
                        }}
                    </style>
                    <script>
                        function copyToClipboard(text) {{
                            navigator.clipboard.writeText(text).then(() => {{
                                alert('Code copied to clipboard!');
                            }});
                        }}
                    </script>
                </head>
                <body>
                    <h1>✅ Authorization Code Received</h1>
                    <p><strong>Code:</strong> <span class="copyable" onclick="copyToClipboard('{code}')">{code}</span></p>
                    <p><strong>State:</strong> {state}</p>
                    <p>You can now copy this code and exchange it for a token.</p>
                </body>
            </html>
        """
    else:
        return "<h1>❌ No authorization code received</h1>", 400

if __name__ == "__main__":
    print("Starting local OAuth callback server on http://localhost:8000/callback")
    app.run(port=8000)
