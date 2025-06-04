from flask import Flask, render_template, request
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.distance import geodesic
import threading
import webbrowser

app = Flask(__name__)
df = pd.read_csv("AP_Temples.csv")

def generate_map(data, center=None, selected_temple=None, nearby_count=None, selected_coords=None, temple_list=None, city=None):
    if center is None:
        center = [data["latitude"].mean(), data["longitude"].mean()]

    m = folium.Map(location=center, zoom_start=12, control_scale=True, width="100%", height="100vh")
    marker_cluster = MarkerCluster().add_to(m)
    temple_details_js = {}

    for _, row in data.iterrows():
        popup_html = f"""
        <div>
            <b>{row['Temple Name']}</b><br>
            {row['City']}<br>
            <a href="#" onclick="showDetails('{row['Temple Name']}'); return false;">Details</a>
        </div>
        """
        popup = folium.Popup(popup_html, max_width=250)
        color = 'red' if row['Temple Name'] == selected_temple else 'blue'
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=popup,
            icon=folium.Icon(color=color)
        ).add_to(marker_cluster)

        images_html = ""
        if 'Image URLs' in row and pd.notna(row['Image URLs']):
            for url in row['Image URLs'].split(','):
                images_html += f'<img src="{url.strip()}" style="width:100%; margin-bottom:5px;">'

        info_html = f"""
            <h4>{row['Temple Name']}</h4>
            <p><b>City:</b> {row['City']}</p>
            <p><b>State:</b> {row['state']}</p>
            <p><b>Country:</b> {row['Country']}</p>
            <p>{row['Description']}</p>
            {images_html}
            <a href="{row['Google Maps Link']}" target="_blank">Google Maps</a>
        """

        speech_text = f"{row['Temple Name']}. Located in {row['City']}, {row['state']}, {row['Country']}. {row['Description']}"
        temple_details_js[row['Temple Name']] = {
            "html": info_html,
            "speech": speech_text
        }

    details_popup_html = f"""
    <div id="details-popup" style="
        position: fixed;
        top: 50px;
        right: 20px;
        width: 320px;
        max-height: 70vh;
        overflow-y: auto;
        background: white;
        border-radius: 8px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        padding: 15px;
        display: none;
        z-index: 10000;
        font-family: Arial, sans-serif;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <button onclick="window.speechSynthesis.cancel(); document.getElementById('details-popup').style.display='none';" 
                style="border: none; background: transparent; font-size: 20px; cursor: pointer;">&times;</button>
            <button id="listen-button" onclick="listenDetails()" 
                style="border: none; background: none; font-size: 16px; cursor: pointer;">🔊 Listen</button>
        </div>
        <div id="details-content" style="margin-top: 10px;"></div>
    </div>

    <script>
        const templeDetails = {temple_details_js};

        function showDetails(name) {{
            const popup = document.getElementById('details-popup');
            const content = document.getElementById('details-content');
            content.innerHTML = templeDetails[name].html;
            popup.style.display = 'block';
            window.currentSpeech = templeDetails[name].speech;
        }}

        function listenDetails() {{
            window.speechSynthesis.cancel();
            let utterance = new SpeechSynthesisUtterance(window.currentSpeech);
            utterance.lang = 'en-US';
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    m.get_root().html.add_child(folium.Element(details_popup_html))

    if nearby_count is not None or temple_list is not None:
        dialog_title = "Nearby Temples" if nearby_count is not None else f"Temples in {city.title()}"
        list_items = ""
        if nearby_count is not None:
            for _, row in data.iterrows():
                if row['Temple Name'] != selected_temple:
                    dist = geodesic(selected_coords, (row['latitude'], row['longitude'])).km
                    list_items += f"<li><b>{row['Temple Name']}</b> - {row['City']} ({dist:.1f} km)</li>"
        elif temple_list:
            for temple in temple_list:
                list_items += f"<li><b>{temple['Temple Name']}</b> - {temple['City']}</li>"

        dialog_html = f"""
        <div id='dialog-box' style='
            position: fixed;
            bottom: 60px;
            right: 10px;
            width: 280px;
            max-height: 300px;
            overflow-y: auto;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
            z-index: 1000;
            display: none;
            font-family: Arial, sans-serif;
        '>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <strong>{dialog_title}</strong>
                <button id="close-dialog" style='
                    background: none;
                    border: none;
                    font-size: 20px;
                    cursor: pointer;
                    line-height: 1;
                '>&times;</button>
            </div>
            <ul style='margin-top: 10px; padding-left: 20px;'>{list_items}</ul>
        </div>

        <button id='open-dialog-btn' style='
            position: fixed;
            bottom: 10px;
            right: 10px;
            padding: 8px 15px;
            font-size: 14px;
            cursor: pointer;
            z-index: 1000;
            border-radius: 5px;
            border: 1px solid #666;
            background: white;
        '>{dialog_title}</button>
        """

        script = """
        <script>
        const dialogBox = document.getElementById('dialog-box');
        const openBtn = document.getElementById('open-dialog-btn');
        const closeBtn = document.getElementById('close-dialog');

        openBtn.addEventListener('click', () => {
            dialogBox.style.display = 'block';
            openBtn.style.display = 'none';
        });

        closeBtn.addEventListener('click', () => {
            dialogBox.style.display = 'none';
            openBtn.style.display = 'block';
        });
        </script>
        """
        m.get_root().html.add_child(folium.Element(dialog_html + script))

    m.get_root().header.add_child(folium.Element('<meta name="viewport" content="width=device-width, initial-scale=1.0">'))
    m.save("static/map.html")
    return "map.html"

@app.route('/')
def index():
    temple_names = sorted(df['Temple Name'].unique())
    return render_template('index.html', temple_names=temple_names)

@app.route('/search_by_city', methods=['POST'])
def search_by_city():
    city = request.form['city']
    filtered = df[df["City"].str.lower().str.contains(city.lower().strip())]
    if not filtered.empty:
        temple_list = filtered[["Temple Name", "City"]].to_dict(orient="records")
        map_file = generate_map(filtered, temple_list=temple_list, city=city)
        return render_template("result.html", map_file=map_file, message=f"Temples in {city.title()}")
    else:
        return render_template("result.html", message="No temples found in this city.")

@app.route('/search_by_temple', methods=['POST'])
def search_by_temple():
    temple_name = request.form['temple']
    filtered_df = df[df["Temple Name"].str.lower() == temple_name.lower().strip()]
    if filtered_df.empty:
        return render_template("result.html", message=f"No temple found with the name '{temple_name}'")

    selected_row = filtered_df.iloc[0]
    selected_coords = (selected_row["latitude"], selected_row["longitude"])

    def is_nearby(row):
        coords = (row["latitude"], row["longitude"])
        return geodesic(selected_coords, coords).km <= 50

    nearby_temples = df[df.apply(is_nearby, axis=1)]
    map_file = generate_map(
        nearby_temples,
        center=selected_coords,
        selected_temple=temple_name,
        nearby_count=len(nearby_temples) - 1,
        selected_coords=selected_coords
    )

    return render_template("result.html", map_file=map_file, message=f"Nearby temples for '{temple_name}'")

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1.5, open_browser).start()
    app.run(host='127.0.0.1', port=5000, debug=True)
