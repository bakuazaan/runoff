import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px

# Load the data
file_path = "wybory.ods"
data = pd.read_excel(file_path, engine="odf")

# Group candidates
grouped_candidates = ["Jakubiak", "Bartoszewicz", "Maciak", "Woch"]
data["Imie"] = data["Imie"].replace(grouped_candidates, "Inni prawica")
# Before grouping, weight proportions by vote count
for col in ["Do Trzaskowskiego", "Do Nawrockiego", "Nie glosuje", "Nie wie"]:
    data[col] = data[col] * data["Liczba glosow"]

# Group by candidate name and sum
data = data.groupby("Imie", as_index=False).sum()

# After summing, convert back to proportions by dividing by total votes
for col in ["Do Trzaskowskiego", "Do Nawrockiego", "Nie glosuje", "Nie wie"]:
    data[col] = data[col] / data["Liczba glosow"]

# Separate voter and non-voter data
non_voter_row = data[data["Imie"] == "Nieglosujacy"]
voter_data = data[data["Imie"] != "Nieglosujacy"]

# Custom candidate order
custom_order = [
    "Trzaskowski", "Nawrocki", "Mentzen", "Braun", "Holownia",
    "Zandberg", "Biejat", "Senyszyn", "Stanowski", "Inni prawica"
]
candidates = [c for c in custom_order if c in voter_data["Imie"].tolist()] + ["Nieglosujacy"]

# Prepare slider values from the dataset
default_values = {}
for _, row in data.iterrows():
    name = row["Imie"]
    if name in grouped_candidates:
        continue  # Already grouped
    trz = row.get("Do Trzaskowskiego", 0.0)
    naw = row.get("Do Nawrockiego", 0.0)
    abstain = row.get("Nie glosuje", 0.0)
    unsure = row.get("Nie wie", 0.0)
    if name == "Nieglosujacy":
        total_votes = data["Liczba glosow"].sum()
        nonvoter_total = row["Liczba glosow"]
        desired_turnout = 0.73 * total_votes
        current_turnout = total_votes - nonvoter_total
        additional_needed = desired_turnout - current_turnout
        if additional_needed < 0:
            turnout_ratio = 0
        else:
            turnout_ratio = min(additional_needed / nonvoter_total, 1.0)

        trz_share = row.get("Do Trzaskowskiego", 0.0) + 0.5 * row.get("Nie wie", 0.0)
        naw_share = row.get("Do Nawrockiego", 0.0) + 0.5 * row.get("Nie wie", 0.0)
        default_values[name] = {
            "trz": round(turnout_ratio * trz_share, 4),
            "naw": round(turnout_ratio * naw_share, 4),
            "none": round(1 - turnout_ratio, 4)
        }
    else:
        default_values[name] = {
            "trz": float(trz + 0.5 * unsure),
            "naw": float(naw + 0.5 * unsure),
            "none": float(abstain)
        }

# Initialize app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Interactive Run-off Vote Projection", style={"textAlign": "center", "color": "#2c3e50"}),
    html.Div([
        html.Div([
            html.H3(candidate, style={"color": "#34495e"}),
            html.Label("To Trzaskowski:"),
            html.Div([
                dcc.Input(id=f"{candidate}-trz-input", type="number", min=0, max=100, step=0.1, style={"width": "60px", "display": "inline-block"}, value=round(default_values.get(candidate, {}).get("trz", 0.5) * 100, 1)),
                html.Span("%", style={"marginLeft": "5px"})
            ], style={"display": "flex", "alignItems": "center"}),
            dcc.Slider(id=f"{candidate}-trz", min=0, max=1, step=0.001, value=default_values.get(candidate, {}).get("trz", 0.5), marks=None, tooltip={"placement": "top"}),
            html.Label("To Nawrocki:"),
            html.Div([
                dcc.Input(id=f"{candidate}-naw-input", type="number", min=0, max=100, step=0.1, style={"width": "60px", "display": "inline-block"}, value=round(default_values.get(candidate, {}).get("naw", 0.5) * 100, 1)),
                html.Span("%", style={"marginLeft": "5px"})
            ], style={"display": "flex", "alignItems": "center"}),
            dcc.Slider(id=f"{candidate}-naw", min=0, max=1, step=0.001, value=default_values.get(candidate, {}).get("naw", 0.5), marks=None, tooltip={"placement": "top"}),
            html.Label("Abstain in run-off:"),
            html.Div([
                dcc.Input(id=f"{candidate}-none-input", type="number", min=0, max=100, step=0.1, style={"width": "60px", "display": "inline-block"}, value=round(default_values.get(candidate, {}).get("none", 0.0) * 100, 1)),
                html.Span("%", style={"marginLeft": "5px"})
            ], style={"display": "flex", "alignItems": "center"}),
            dcc.Slider(id=f"{candidate}-none", min=0, max=1, step=0.001, value=default_values.get(candidate, {}).get("none", 0.0), marks=None, tooltip={"placement": "top"}),
            html.Div("Ensure total does not exceed 1. Unused share will be split 50/50.", style={"fontSize": "12px", "color": "#888"})
        ], style={"border": "1px solid #ccc", "padding": "15px", "margin": "10px", "width": "280px", "borderRadius": "10px", "boxShadow": "2px 2px 8px rgba(0,0,0,0.1)", "backgroundColor": "#f9f9f9"})
        for candidate in candidates
    ], style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"}),
    html.Div(id="validation-warning", style={"color": "red", "fontSize": "16px", "marginTop": "10px"}),
    html.Div([
        html.Button("Reset to Defaults", id="reset-button", style={"margin": "10px", "padding": "10px 20px", "fontSize": "14px", "backgroundColor": "#bdc3c7", "color": "#2c3e50", "border": "none", "borderRadius": "5px"}),
        html.Button("Update Projection", id="update-button", style={"margin": "20px", "padding": "12px 24px", "fontSize": "16px", "backgroundColor": "#2980b9", "color": "white", "border": "none", "borderRadius": "5px"}),
        dcc.Graph(id="result-pie"),
        html.Div(id="summary", style={"fontSize": "18px", "marginTop": "20px", "color": "#2c3e50"})
    ], style={"textAlign": "center"})
])

# Sync sliders with input fields and vice versa
@app.callback(
    [Output(f"{candidate}-{field}", "value") for candidate in candidates for field in ["trz", "naw", "none"]] +
    [Output(f"{candidate}-{field}-input", "value") for candidate in candidates for field in ["trz", "naw", "none"]],
    [Input(f"{candidate}-{field}-input", "value") for candidate in candidates for field in ["trz", "naw", "none"]] +
    [Input(f"{candidate}-{field}", "value") for candidate in candidates for field in ["trz", "naw", "none"]] +
    [Input("reset-button", "n_clicks")]
)
def sync_sliders_and_inputs_and_reset(*values):
    num_fields = len(candidates) * 3
    input_vals = values[:num_fields]
    slider_vals = values[num_fields:2*num_fields]
    n_clicks = values[-1]

    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "reset-button.n_clicks":
        default_inputs = [round(default_values[candidate][field] * 100, 1)
                          for candidate in candidates for field in ["trz", "naw", "none"]]
        default_sliders = [round(v / 100, 3) for v in default_inputs]
        return default_sliders + default_inputs

    updated_sliders = [slider_vals[i] if ctx.triggered and "-trz-input" not in ctx.triggered[0]['prop_id'] and "-naw-input" not in ctx.triggered[0]['prop_id'] and "-none-input" not in ctx.triggered[0]['prop_id'] else round((input_vals[i] or 0) / 100, 3) for i in range(num_fields)]
    updated_inputs = [input_vals[i] if ctx.triggered and "-trz" not in ctx.triggered[0]['prop_id'] and "-naw" not in ctx.triggered[0]['prop_id'] and "-none" not in ctx.triggered[0]['prop_id'] else round((slider_vals[i] or 0) * 100, 1) for i in range(num_fields)]
    return updated_sliders + updated_inputs

@app.callback(
    [Output("validation-warning", "children")],
    [Input(f"{candidate}-{field}-input", "value") for field in ["trz", "naw", "none"] for candidate in candidates]
)
def validate_totals(*inputs):
    warnings = []
    num_candidates = len(candidates)
    for i, candidate in enumerate(candidates):
        trz = inputs[i]
        naw = inputs[i + num_candidates]
        none = inputs[i + 2 * num_candidates]
        total = (trz or 0) + (naw or 0) + (none or 0)
        if total > 100.1:
            warnings.append(f"⚠️ {candidate}: Total exceeds 100%.")
    return [" ".join(warnings)]

@app.callback(
    [Output("result-pie", "figure"),
     Output("summary", "children")],
    Input("update-button", "n_clicks"),
    [State(f"{candidate}-trz", "value") for candidate in candidates] +
    [State(f"{candidate}-naw", "value") for candidate in candidates] +
    [State(f"{candidate}-none", "value") for candidate in candidates]
)
def update_projection(n_clicks, *values):
    trz_votes = 0
    naw_votes = 0

    trz_values = values[:len(candidates)]
    naw_values = values[len(candidates):2*len(candidates)]
    none_values = values[2*len(candidates):]

    for i, candidate in enumerate(candidates):
        if candidate == "Nieglosujacy":
            vote_fraction = trz_values[i] + naw_values[i] + none_values[i]
            total_nonvoters = non_voter_row["Liczba glosow"].values[0]
            votes = total_nonvoters * vote_fraction
        else:
            votes = voter_data[voter_data["Imie"] == candidate]["Liczba glosow"].values[0]

        undecided = 1 - (trz_values[i] + naw_values[i] + none_values[i])
        if undecided < 0:
            undecided = 0

        trz_votes += votes * (trz_values[i] + 0.5 * undecided)
        naw_votes += votes * (naw_values[i] + 0.5 * undecided)

    fig = px.pie(values=[trz_votes, naw_votes], names=["Trzaskowski", "Nawrocki"],
                 title="Projected Run-off Result", hole=0.4, color_discrete_sequence=["#3498db", "#e74c3c"])
    fig.update_traces(textposition='inside', texttemplate='%{label}: %{percent:.2%}')

    summary = f"Projected Votes — Trzaskowski: {trz_votes:,.0f}, Nawrocki: {naw_votes:,.0f}"

    return fig, summary


if __name__ == '__main__':
    app.run(debug=True)
