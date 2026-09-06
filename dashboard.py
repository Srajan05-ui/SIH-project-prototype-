"""
Stage 6 â€” dashboard with CPI Calculator.

Run with:
    streamlit run dashboard.py

Reads directly from Postgres on every page load/refresh.
"""
import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine

st.set_page_config(page_title="AirPrice India â€” Prototype", layout="wide")
st.title("âœˆï¸ AirPrice India â€” Airfare Index Prototype")
st.caption(
    "SIH26056 internal hackathon prototype. Route-level index only; "
    "see docs/PRD_hackathon_prototype.md for scope."
)

engine = get_engine()


@st.cache_data(ttl=60)
def load_fares() -> pd.DataFrame:
    df = pd.read_sql(
        text(
            "SELECT * FROM fare_observations_clean "
            "WHERE is_duplicate = FALSE AND is_outlier = FALSE AND price IS NOT NULL "
            "ORDER BY observed_at_utc"
        ),
        engine,
    )
    df["observed_at_ist"] = pd.to_datetime(df["observed_at_utc"], utc=True).dt.tz_convert('Asia/Kolkata')
    return df


@st.cache_data(ttl=60)
def load_index() -> pd.DataFrame:
    df = pd.read_sql(
        text("SELECT * FROM airfare_index ORDER BY computed_at_utc"),
        engine,
    )
    if not df.empty:
        df["computed_at_ist"] = pd.to_datetime(df["computed_at_utc"], utc=True).dt.tz_convert('Asia/Kolkata')
    return df


@st.cache_data(ttl=60)
def load_official_cpi() -> pd.DataFrame:
    try:
        df = pd.read_sql(
            text("SELECT * FROM official_cpi WHERE state = 'All India' AND sector = 'Combined' AND item = 'Airfare'"),
            engine,
        )
        return df
    except Exception:
        # Table might not exist yet if process_cpi_excel.py wasn't run
        return pd.DataFrame()


fares_df = load_fares()
index_df = load_index()
official_cpi_df = load_official_cpi()

if fares_df.empty:
    st.warning(
        "No cleaned data yet. Run collector_tier1.py / collector_tier2_airline.py, "
        "then cleaning.py, before this dashboard has anything to show."
    )
    st.stop()

fares_df["route"] = fares_df["origin"] + " â†’ " + fares_df["destination"]
routes = sorted(fares_df["route"].unique())

import plotly.graph_objects as go

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAP COORDINATES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AIRPORT_COORDS = {
    "DEL": {"lat": 28.5562, "lon": 77.1000, "name": "New Delhi"},
    "BOM": {"lat": 19.0896, "lon": 72.8656, "name": "Mumbai"},
    "BLR": {"lat": 13.1986, "lon": 77.7066, "name": "Bengaluru"},
    "HYD": {"lat": 17.2403, "lon": 78.4294, "name": "Hyderabad"},
    "CCU": {"lat": 22.6520, "lon": 88.4467, "name": "Kolkata"},
    "MAA": {"lat": 12.9941, "lon": 80.1709, "name": "Chennai"},
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 1: Interactive Route Map
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("ðŸ—ºï¸ Live Monitored Flight Routes")

fig = go.Figure()

# Plot lines for active routes in the database
active_routes = fares_df[["origin", "destination"]].drop_duplicates()
for _, row in active_routes.iterrows():
    orig = row["origin"]
    dest = row["destination"]
    
    if orig in AIRPORT_COORDS and dest in AIRPORT_COORDS:
        # Get latest CPI/Fare data for this route for the hover text
        route_data = fares_df[(fares_df["origin"] == orig) & (fares_df["destination"] == dest)]
        latest_date = route_data["observed_at_ist"].dt.date.max()
        curr_price = route_data[route_data["observed_at_ist"].dt.date == latest_date]["price"].mean()
        
        fig.add_trace(
            go.Scattermap(
                mode="lines",
                lon=[AIRPORT_COORDS[orig]["lon"], AIRPORT_COORDS[dest]["lon"]],
                lat=[AIRPORT_COORDS[orig]["lat"], AIRPORT_COORDS[dest]["lat"]],
                line=dict(width=2.5, color='#00d4ff'), # Glowing cyan airline route
                hoverinfo='text',
                text=f"<b>Route:</b> {orig} âœˆï¸ {dest}<br><b>Current Avg:</b> â‚¹{curr_price:,.0f}",
                name=f"{orig}-{dest}"
            )
        )

# Plot all known airports as markers with visible city labels
lats = [coords["lat"] for coords in AIRPORT_COORDS.values()]
lons = [coords["lon"] for coords in AIRPORT_COORDS.values()]
city_names = [coords['name'] for coords in AIRPORT_COORDS.values()]
hover_texts = [f"{code} Airport" for code in AIRPORT_COORDS.keys()]

fig.add_trace(go.Scattermap(
    mode="markers+text",
    lon=lons,
    lat=lats,
    hoverinfo='text',
    hovertext=hover_texts,
    text=city_names,
    textposition="top center",
    textfont=dict(color="black", size=18, family="Arial Black, sans-serif"),
    marker=dict(size=18, color='red', opacity=1.0),
    name="Airports"
))

fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    height=600,
    showlegend=False,
    map=dict(
        style="open-street-map",  # Bright, detailed, and highly visible base map
        center=dict(lat=21.0, lon=78.0),
        zoom=3.8,
        pitch=0,
    ),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)'
)

st.plotly_chart(fig, width='stretch')
st.divider()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 2: Index + Fare Trend
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Latest index value per route")
    if index_df.empty:
        st.info("No index computed yet. Run index_calc.py.")
    else:
        latest_idx = index_df.sort_values("computed_at_ist").groupby(["origin", "destination"]).tail(1)
        latest_idx = latest_idx.assign(route=latest_idx["origin"] + " â†’ " + latest_idx["destination"])
        for _, row in latest_idx.iterrows():
            delta = row["index_value"] - 100.0
            st.metric(row["route"], f"{row['index_value']:.1f}", f"{delta:+.1f} vs base")

with col2:
    st.subheader("Route-wise fare trend")
    selected_route = st.selectbox("Route", routes)
    route_df = fares_df[fares_df["route"] == selected_route]
    chart_df = route_df.pivot_table(
        index="booking_window_days", columns="source_tier", values="price", aggfunc="mean"
    )
    st.line_chart(chart_df, x_label="Booking Window (Days Ahead)", y_label="Average Price (INR)")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 2: Recent Observations Table
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.subheader("Recent observations")
st.dataframe(
    fares_df.sort_values("observed_at_ist", ascending=False)
    .head(50)[["observed_at_ist", "route", "source_tier", "airline", "price", "booking_window_days"]],
    width='stretch',
)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 3: PRICE BREAKDOWN
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.divider()
st.header("ðŸ’° Price Breakdown Analysis")
st.markdown("Detailed fare analysis by airline, booking window, and price distribution for any route.")

import plotly.express as px

pb_route = st.selectbox("Select Route for Price Breakdown", routes, key="pb_route")
pb_origin, pb_dest = pb_route.split(" â†’ ")
pb_df = fares_df[
    (fares_df["origin"] == pb_origin) &
    (fares_df["destination"] == pb_dest) &
    (fares_df["source_tier"] == "tier1_google_flights")
].copy()

if pb_df.empty:
    st.warning("No Tier 1 data available for this route yet.")
else:
    # â”€â”€ ROW 1: Key Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.subheader("ðŸ“Š Key Price Statistics")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Lowest Fare", f"â‚¹{pb_df['price'].min():,.0f}")
    k2.metric("Highest Fare", f"â‚¹{pb_df['price'].max():,.0f}")
    k3.metric("Average Fare", f"â‚¹{pb_df['price'].mean():,.0f}")
    k4.metric("Median Fare",  f"â‚¹{pb_df['price'].median():,.0f}")
    k5.metric("Total Samples", f"{len(pb_df):,}")

    st.divider()

    # â”€â”€ ROW 2: Airline Comparison + Price Distribution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.subheader("âœˆï¸ Airline-wise Price Comparison")
        airline_stats = (
            pb_df.groupby("airline")["price"]
            .agg(Min="min", Avg="mean", Max="max", Count="count")
            .reset_index()
            .sort_values("Avg")
        )
        airline_stats["Avg"] = airline_stats["Avg"].round(0)
        airline_stats["Min"] = airline_stats["Min"].round(0)
        airline_stats["Max"] = airline_stats["Max"].round(0)

        fig_airline = px.bar(
            airline_stats,
            x="airline",
            y="Avg",
            error_y=airline_stats["Max"] - airline_stats["Avg"],
            error_y_minus=airline_stats["Avg"] - airline_stats["Min"],
            color="Avg",
            color_continuous_scale="Blues",
            text="Avg",
            labels={"airline": "Airline", "Avg": "Avg Fare (₹)"},
        )
        fig_airline.update_traces(
            texttemplate="₹%{text:,.0f}",
            textposition="outside",
            marker_line_width=1,
            marker_line_color="white",
        )
        fig_airline.update_layout(
            coloraxis_showscale=False,
            margin=dict(t=20, b=10),
            xaxis_title="Airline",
            yaxis_title="Average Price (₹)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_airline.add_annotation(
            text="Error bars show Min–Max range",
            xref="paper", yref="paper",
            x=0, y=-0.18, showarrow=False,
            font=dict(size=10, color="grey"),
        )
        st.plotly_chart(fig_airline, width='stretch')
        st.caption("Bar height = average fare. Error bars show the cheapest and most expensive fares seen per airline.")

    with col_b:
        st.subheader("ðŸ“¦ Price Distribution (Box Plot)")
        fig_box = px.box(
            pb_df,
            x="airline",
            y="price",
            color="airline",
            points="all",
            labels={"airline": "Airline", "price": "Price (â‚¹)"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_box.update_layout(
            showlegend=False,
            margin=dict(t=20, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Airline",
            yaxis_title="Price (â‚¹)",
        )
        st.plotly_chart(fig_box, width='stretch')
        st.caption("Each dot is a real fare observation. The box shows the 25thâ€“75th percentile range. Dots outside = potential outliers.")

    st.divider()

    # â”€â”€ ROW 3: Booking Window Curve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.subheader("ðŸ“… How Price Changes with Days to Departure")
    window_stats = (
        pb_df.groupby(["booking_window_days", "airline"])["price"]
        .mean()
        .reset_index()
        .rename(columns={"price": "Avg Price"})
    )
    fig_window = px.line(
        window_stats,
        x="booking_window_days",
        y="Avg Price",
        color="airline",
        markers=True,
        labels={"booking_window_days": "Days Before Departure", "Avg Price": "Avg Fare (â‚¹)", "airline": "Airline"},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig_window.update_layout(
        margin=dict(t=20, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(autorange="reversed", title="Days Before Departure (Higher = Further Ahead)"),
        yaxis_title="Average Fare (â‚¹)",
    )
    fig_window.add_vrect(
        x0=0, x1=5,
        fillcolor="red", opacity=0.07,
        annotation_text="Last-minute zone",
        annotation_position="top left",
    )
    fig_window.add_vrect(
        x0=20, x1=35,
        fillcolor="green", opacity=0.07,
        annotation_text="Best booking zone",
        annotation_position="top right",
    )
    st.plotly_chart(fig_window, width='stretch')
    st.caption("Left side = last-minute booking (expensive). Right side = advance booking. Sweet spot is usually 14â€“30 days ahead.")

    st.divider()

    # â”€â”€ ROW 4: Cheapest Airline Leaderboard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.subheader("ðŸ† Airline Price Leaderboard (Cheapest First)")
    leaderboard = airline_stats.sort_values("Avg")[["airline", "Min", "Avg", "Max", "Count"]].copy()
    leaderboard.columns = ["Airline", "Cheapest Seen (â‚¹)", "Avg Fare (â‚¹)", "Most Expensive (â‚¹)", "Observations"]
    leaderboard["Cheapest Seen (â‚¹)"] = leaderboard["Cheapest Seen (â‚¹)"].apply(lambda x: f"â‚¹{x:,.0f}")
    leaderboard["Avg Fare (â‚¹)"] = leaderboard["Avg Fare (â‚¹)"].apply(lambda x: f"â‚¹{x:,.0f}")
    leaderboard["Most Expensive (â‚¹)"] = leaderboard["Most Expensive (â‚¹)"].apply(lambda x: f"â‚¹{x:,.0f}")

    # Highlight cheapest airline
    cheapest = leaderboard.iloc[0]["Airline"]
    st.success(f"âœ… **Cheapest airline on {pb_route}:** {cheapest} (based on {len(pb_df)} real scraped fares)")
    st.dataframe(leaderboard, width='stretch', hide_index=True)

    # ── ROW 5: TAX & FEE BREAKDOWN ───────────────────────────────────────────
    st.divider()
    st.subheader("Fare Tax & Fee Breakdown (Estimated)")
    st.info(
        "NOTE: Google Flights provides only the all-inclusive total fare. "
        "This breakdown is ESTIMATED using India's published aviation tax rules "
        "(DGCA / CBIC circular) applied to the average fare for this route. "
        "Actual airline itemization may vary slightly."
    )

    avg_fare = pb_df["price"].mean()

    # Indian Aviation Tax Structure (Economy class, domestic one-way)
    AIRPORT_LEVIES = {
        "DEL": 560,   # IGI: UDF Rs325 + PSF Rs50 + ADF Rs179 + CUTE Rs6
        "BOM": 262,   # CSIA: UDF Rs150 + PSF Rs50 + ADF Rs50 + CUTE Rs12
        "BLR": 385,   # KIA: UDF Rs250 + PSF Rs50 + ADF Rs85
        "HYD": 340,
        "CCU": 290,
        "MAA": 310,
    }
    origin_levy       = AIRPORT_LEVIES.get(pb_origin, 350)
    dest_levy         = AIRPORT_LEVIES.get(pb_dest,   350)
    total_airport_levy = origin_levy + dest_levy
    PSF_SECURITY      = 150   # Passenger Service Fee flat domestic

    fixed_govt  = total_airport_levy + PSF_SECURITY
    variable    = max(avg_fare - fixed_govt, 0)

    # variable = (Base + Fuel) * 1.05   (5% GST economy)
    # Base : Fuel = 76 : 24
    variable_pre_gst = variable / 1.05
    base_fare        = round(variable_pre_gst * 0.76)
    fuel_surcharge   = round(variable_pre_gst * 0.24)
    gst_amount       = round(variable - base_fare - fuel_surcharge)

    components = {
        "Base Fare (Seat Cost)":             base_fare,
        "Fuel Surcharge / YQ":              fuel_surcharge,
        "GST (5% on Base + Fuel)":          gst_amount,
        "Airport User Dev. Fee (UDF)":      total_airport_levy,
        "Passenger Service Fee (PSF/ASF)":  PSF_SECURITY,
    }
    total_check = sum(components.values())

    import plotly.graph_objects as go2
    tax_col1, tax_col2 = st.columns([1, 1])

    with tax_col1:
        labels = list(components.keys())
        values = list(components.values())
        colors_donut = ["#1565c0", "#ff6f00", "#c62828", "#2e7d32", "#6a1b9a"]
        fig_donut = go2.Figure(data=[go2.Pie(
            labels=labels,
            values=values,
            hole=0.52,
            marker=dict(colors=colors_donut, line=dict(color="#ffffff", width=2)),
            textinfo="label+percent",
            textfont_size=10,
        )])
        fig_donut.update_layout(
            annotations=[dict(
                text=f"<b>Rs {avg_fare:,.0f}</b><br>Total Fare",
                x=0.5, y=0.5, font_size=13, showarrow=False,
                font_color="#1565c0",
            )],
            showlegend=False,
            margin=dict(t=20, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with tax_col2:
        st.markdown(f"#### Avg fare on {pb_route}: Rs {avg_fare:,.0f}")
        st.markdown("---")
        import pandas as pd2
        breakdown_rows = []
        for comp, amt in components.items():
            pct = (amt / avg_fare * 100) if avg_fare > 0 else 0
            tag = "Tax/Levy" if any(w in comp for w in ["GST", "Fee", "UDF"]) else "Airline Revenue"
            breakdown_rows.append({"Component": comp, "Amount": f"Rs {amt:,.0f}", "% of Fare": f"{pct:.1f}%", "Type": tag})
        st.dataframe(pd2.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)

        tax_total = gst_amount + total_airport_levy + PSF_SECURITY
        tax_pct   = (tax_total / avg_fare * 100) if avg_fare > 0 else 0
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("Taxes & Govt Levies", f"Rs {tax_total:,.0f}", f"{tax_pct:.1f}% of total")
        col_t2.metric("Airline Revenue", f"Rs {base_fare + fuel_surcharge:,.0f}", f"{100-tax_pct:.1f}% of total")
        st.caption(
            "Estimated using DGCA/CBIC rates: GST 5% economy, UDF per AERA airport tariff "
            "orders, PSF Rs150 flat domestic. Fuel surcharge ~24% of variable fare component."
        )

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 4: CPI CALCULATOR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.divider()

st.header("ðŸ§® Airfare CPI Calculator")
st.markdown(
    """
    **Formula (Laspeyres Fixed-Basket Index â€” same methodology as India's official CPI):**

    > `Airfare CPI = 100 Ã— (Current Avg Fare) Ã· (Base Period Avg Fare)`

    | Term | Meaning |
    |---|---|
    | **Base Period** | Earliest date with cleaned data for a route. CPI = 100 on this date. |
    | **CPI > 100** | Fares have risen â†’ Airfare **Inflation** ðŸ“ˆ |
    | **CPI < 100** | Fares have fallen â†’ Airfare **Deflation** ðŸ“‰ |
    | **National CPI** | Weighted average of all route CPIs (weight = observation count as proxy for passenger volume) |
    """
)

cpi_col1, cpi_col2 = st.columns([1, 1])

with cpi_col1:
    st.subheader("ðŸ“ Route-Level CPI")

    cpi_route = st.selectbox("Select Route for CPI", routes, key="cpi_route")
    origin_c, dest_c = cpi_route.split(" â†’ ")
    route_data = fares_df[(fares_df["origin"] == origin_c) & (fares_df["destination"] == dest_c)]

    if route_data.empty:
        st.warning("No data available for this route.")
    else:
        base_date = route_data["observed_at_ist"].dt.date.min()
        base_data = route_data[route_data["observed_at_ist"].dt.date == base_date]
        base_price = base_data["price"].mean()

        latest_date = route_data["observed_at_ist"].dt.date.max()
        current_data = route_data[route_data["observed_at_ist"].dt.date == latest_date]
        current_price = current_data["price"].mean()

        if base_price > 0 and not pd.isna(base_price) and not pd.isna(current_price):
            cpi_value = 100.0 * current_price / base_price
            delta = cpi_value - 100.0

            st.metric(
                label=f"CPI for {cpi_route}",
                value=f"{cpi_value:.2f}",
                delta=f"{delta:+.2f} vs Base (100)",
                delta_color="inverse",  # red = higher price = bad for consumer
            )

            # Show the formula worked out step-by-step
            st.markdown("**Formula Breakdown:**")
            st.code(
                f"Base Period  : {base_date}  â†’  Avg Fare = â‚¹{base_price:,.0f}\n"
                f"Current Date : {latest_date}  â†’  Avg Fare = â‚¹{current_price:,.0f}\n"
                f"\nCPI = 100 Ã— {current_price:,.0f} Ã· {base_price:,.0f} = {cpi_value:.2f}",
                language="text",
            )

            if delta > 0.01:
                st.error(f"ðŸ”´ Airfare INFLATION of {delta:.2f}% detected on this route since base period.")
            elif delta < -0.01:
                st.success(f"ðŸŸ¢ Airfare DEFLATION of {abs(delta):.2f}% detected on this route since base period.")
            else:
                st.info("âšª Fares are stable â€” no meaningful change from base period.")
        else:
            st.warning("Cannot compute CPI: base price is zero or missing.")

with cpi_col2:
    st.subheader("ðŸ‡®ðŸ‡³ National Aggregate Airfare CPI")

    national_rows = []
    for (origin, dest), grp in fares_df.groupby(["origin", "destination"]):
        base_d = grp["observed_at_ist"].dt.date.min()
        base_p = grp[grp["observed_at_ist"].dt.date == base_d]["price"].mean()
        latest_d = grp["observed_at_ist"].dt.date.max()
        curr_p = grp[grp["observed_at_ist"].dt.date == latest_d]["price"].mean()
        n = len(grp)
        if base_p > 0 and not pd.isna(base_p) and not pd.isna(curr_p):
            cpi_val = 100.0 * curr_p / base_p
            national_rows.append({
                "route": f"{origin} â†’ {dest}",
                "Base Fare (â‚¹)": round(base_p, 2),
                "Current Fare (â‚¹)": round(curr_p, 2),
                "CPI": round(cpi_val, 2),
                "Obs. Count (Weight)": n,
                "_cpi_raw": cpi_val,
                "_weight": n,
            })

    if national_rows:
        nat_df = pd.DataFrame(national_rows)
        total_weight = nat_df["_weight"].sum()
        national_cpi = (nat_df["_cpi_raw"] * nat_df["_weight"]).sum() / total_weight
        nat_delta = national_cpi - 100.0

        st.metric(
            label="National Airfare CPI (Passenger-Weighted Avg)",
            value=f"{national_cpi:.2f}",
            delta=f"{nat_delta:+.2f} vs Base (100)",
            delta_color="inverse",
        )

        st.markdown("**Route-wise CPI Breakdown:**")
        display_df = nat_df[["route", "Base Fare (â‚¹)", "Current Fare (â‚¹)", "CPI", "Obs. Count (Weight)"]].copy()
        st.dataframe(display_df, width='stretch', hide_index=True)

        st.markdown("**Route CPI Bar Chart:**")
        import plotly.express as px
        
        # Professional color-coded bar chart based on inflation (CPI > 100 = Red, CPI < 100 = Green)
        fig_bar = px.bar(
            nat_df,
            x="route",
            y="CPI",
            color="CPI",
            color_continuous_scale="RdYlGn_r",
            color_continuous_midpoint=100,
            text="CPI",
            labels={"route": "Flight Sector", "CPI": "CPI Value (100 = Base Price)"}
        )
        fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside', marker_line_width=1, marker_line_color='black')
        
        # Set y-axis range to emphasize changes around 100
        min_y = min(90, nat_df["CPI"].min() - 5)
        max_y = max(110, nat_df["CPI"].max() + 10)
        
        fig_bar.update_layout(
            yaxis=dict(range=[min_y, max_y]),
            coloraxis_colorbar=dict(title="Inflation Scale"),
            margin=dict(t=20, b=20)
        )
        
        # Add a baseline at 100 to clearly show inflation vs deflation
        fig_bar.add_hline(y=100, line_dash="dash", line_color="white", annotation_text="Base Price (100)", annotation_position="bottom right")
        
        st.plotly_chart(fig_bar, width='stretch')

        if nat_delta > 0.01:
            st.error(f"ðŸ”´ National airfare is {nat_delta:.2f}% ABOVE the base period â€” overall inflation signal.")
        elif nat_delta < -0.01:
            st.success(f"ðŸŸ¢ National airfare is {abs(nat_delta):.2f}% BELOW the base period â€” overall deflation signal.")
        else:
            st.info("âšª National airfare is stable at the base level.")
            
        st.divider()
        st.subheader("ðŸ›ï¸ Official MoSPI Benchmark (Airfare)")
        if not official_cpi_df.empty:
            latest_official = official_cpi_df.sort_values(["year", "month"]).iloc[-1]
            st.markdown(f"**Latest official data point ({latest_official['month']} {latest_official['year']})**")
            
            o_cpi = latest_official['cpi_index']
            o_inf = latest_official['inflation']
            
            st.metric(
                label="Official MoSPI Airfare CPI (Base 2024=100)",
                value=f"{o_cpi:.2f}",
                delta=f"{o_inf:.2f}% YoY Inflation",
                delta_color="inverse"
            )
            
            gap = national_cpi - o_cpi
            st.info(f"**Prototype vs Official Gap:** Our live scraped CPI is **{abs(gap):.2f} points {'higher' if gap > 0 else 'lower'}** than the latest official MoSPI benchmark.")
            
        else:
            st.info("Official MoSPI CPI data not loaded yet. Run `process_cpi_excel.py`.")
            
    else:
        st.warning("Not enough data to compute national CPI yet.")

st.caption(
    "Anomaly flags are surfaced by anomaly.py's log output for this prototype "
    "(see docs/DESIGN_hackathon_prototype.md Â§5) rather than a table here â€” "
    "run `python anomaly.py` alongside the dashboard during a demo."
)

