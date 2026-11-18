import pandas as pd
import html

# Read the Excel file
df = pd.read_excel(".tmp/indeed_social_media_manager_jobs.xlsx")
total_jobs = len(df)

# Get city stats
cities = (
    df["Location"].value_counts().head(5).to_dict() if "Location" in df.columns else {}
)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Media Manager Jobs</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }}
        .stat {{ background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; border: 2px solid transparent; }}
        .stat:hover {{ background: rgba(255,255,255,0.3); transform: translateY(-2px); }}
        .stat.active {{ background: rgba(255,255,255,0.4); border: 2px solid white; }}
        .stat-number {{ font-size: 24px; font-weight: bold; }}
        .stat-label {{ font-size: 12px; opacity: 0.9; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        thead {{ background: #f8f9fa; position: sticky; top: 0; }}
        th {{ padding: 15px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #e9ecef; }}
        td {{ padding: 15px; border-bottom: 1px solid #e9ecef; vertical-align: top; }}
        tr:hover {{ background: #f8f9fa; }}
        .job-title {{ color: #667eea; font-weight: 600; min-width: 180px; }}
        .salary {{ color: #28a745; font-weight: 500; }}
        .location {{ color: #666; min-width: 100px; }}
        .job-type {{ min-width: 100px; }}
        .description {{ color: #444; line-height: 1.6; font-size: 14px; max-width: 400px; }}
        a {{ color: #667eea; text-decoration: none; font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
        .controls {{ margin-bottom: 20px; display: flex; gap: 10px; align-items: center; }}
        input, select {{ padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }}
        button {{ padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: 500; transition: background 0.3s ease; }}
        button:hover {{ background: #764ba2; }}
        input {{ width: 300px; }}
        .count {{ color: #666; font-size: 14px; }}
        .filter-info {{ background: #e7f3ff; border-left: 4px solid #667eea; padding: 12px; border-radius: 4px; margin-bottom: 20px; color: #333; display: none; }}
        .filter-info.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Social Media Manager Job Listings</h1>
            <p>Indeed.com - Top 5 US Cities</p>
            <div class="stats" id="cityStats">
"""

# Add city stats as clickable buttons
for city, count in cities.items():
    html_content += f"""                <div class="stat" onclick="filterByCity('{city}', this)">
                    <div class="stat-number">{count}</div>
                    <div class="stat-label">{str(city)}</div>
                </div>
"""

# Add total jobs button
html_content += f"""                <div class="stat total-stat" onclick="showAllJobs(this)" style="cursor: pointer;">
                    <div class="stat-number">{total_jobs}</div>
                    <div class="stat-label">All Jobs</div>
                </div>
            </div>
        </div>

        <div class="filter-info" id="filterInfo"></div>

        <div class="controls">
            <input type="text" id="searchInput" placeholder="Search by title, company...">
            <button onclick="filterTable()">Search</button>
            <button onclick="resetFilters()">Reset All</button>
            <span class="count" id="count">Showing all jobs</span>
        </div>

        <table id="jobsTable">
            <thead>
                <tr>
                    <th style="width: 20%;">Title</th>
                    <th style="width: 12%;">Location</th>
                    <th style="width: 12%;">Salary</th>
                    <th style="width: 10%;">Type</th>
                    <th style="width: 40%;">Job Description</th>
                    <th style="width: 6%;">Link</th>
                </tr>
            </thead>
            <tbody>
"""

# Add table rows
for idx, row in df.iterrows():
    title = html.escape(str(row.get("Title", "N/A")))
    location = html.escape(str(row.get("Location", "N/A")))
    salary = html.escape(str(row.get("Salary", "N/A")))
    job_type = html.escape(str(row.get("Job Type", "N/A")))

    full_desc = str(row.get("Full Description", ""))
    if full_desc and full_desc.strip() and full_desc.lower() != "nan":
        description = html.escape(full_desc[:300].strip())
    else:
        description = html.escape(
            str(row.get("Description Snippet", "No description available"))[
                :300
            ].strip()
        )

    job_url = str(row.get("Job URL", "#"))

    html_content += f"""                <tr class="job-row" data-location="{location}">
                    <td class="job-title">{title}</td>
                    <td class="location">{location}</td>
                    <td class="salary">{salary}</td>
                    <td class="job-type">{job_type}</td>
                    <td class="description">{description}...</td>
                    <td><a href="{job_url}" target="_blank">View</a></td>
                </tr>
"""

html_content += """            </tbody>
        </table>
    </div>

    <script>
        let currentFilter = null;

        function filterByCity(city, element) {
            currentFilter = city;

            // Update button styling
            document.querySelectorAll('.stat').forEach(stat => {
                stat.classList.remove('active');
            });
            element.classList.add('active');

            // Show filter info
            const filterInfo = document.getElementById('filterInfo');
            filterInfo.textContent = `Filtered by: ${city}`;
            filterInfo.classList.add('active');

            // Filter table
            const rows = document.querySelectorAll('.job-row');
            let visible = 0;

            rows.forEach(row => {
                const location = row.getAttribute('data-location');
                if (location === city) {
                    row.style.display = '';
                    visible++;
                } else {
                    row.style.display = 'none';
                }
            });

            document.getElementById('count').textContent = `Showing ${visible} jobs in ${city}`;
            document.getElementById('searchInput').value = '';
        }

        function showAllJobs(element) {
            currentFilter = null;

            // Update button styling
            document.querySelectorAll('.stat').forEach(stat => {
                stat.classList.remove('active');
            });
            element.classList.add('active');

            // Hide filter info
            const filterInfo = document.getElementById('filterInfo');
            filterInfo.classList.remove('active');

            // Show all rows
            const rows = document.querySelectorAll('.job-row');
            rows.forEach(row => {
                row.style.display = '';
            });

            document.getElementById('count').textContent = `Showing all ${rows.length} jobs`;
            document.getElementById('searchInput').value = '';
        }

        function filterTable() {
            const input = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('.job-row');
            let visible = 0;

            rows.forEach(row => {
                // Only search within currently visible rows
                if (row.style.display === 'none' && currentFilter) {
                    return;
                }

                const text = row.textContent.toLowerCase();
                if (text.includes(input)) {
                    row.style.display = '';
                    visible++;
                } else {
                    row.style.display = 'none';
                }
            });

            if (currentFilter) {
                document.getElementById('count').textContent = `Showing ${visible} jobs in ${currentFilter} (filtered by search)`;
            } else {
                document.getElementById('count').textContent = `Showing ${visible} jobs`;
            }
        }

        function resetFilters() {
            currentFilter = null;
            document.getElementById('searchInput').value = '';

            // Clear active button
            document.querySelectorAll('.stat').forEach(stat => {
                stat.classList.remove('active');
            });

            // Hide filter info
            document.getElementById('filterInfo').classList.remove('active');

            // Show all rows
            const rows = document.querySelectorAll('.job-row');
            rows.forEach(row => {
                row.style.display = '';
            });

            document.getElementById('count').textContent = `Showing all ${rows.length} jobs`;
        }

        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') filterTable();
        });
    </script>
</body>
</html>
"""

with open(".tmp/indeed_preview.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML updated with clickable city filters")
