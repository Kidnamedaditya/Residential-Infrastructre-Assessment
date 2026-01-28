# Real-Time Residential Infrastructure Intelligence Platform

An AI-powered property inspection system built with Snowflake, Streamlit, and Cortex AI.

## Features
- **Dual User Modes**: Normal User (Homeowners/Buyers) and Professional Inspectors.
- **AI Inspection**: Automated defect detection and risk scoring using Snowflake Cortex & Vision AI.
- **Real-time Monitoring**: Continuous risk assessment via Snowflake Streams & Tasks.
- **Premium UI**: Modern Streamlit interface with glassmorphism design.

## Tech Stack
- **Database**: Snowflake (SQL, Views, Cortex, Streams)
- **Frontend**: Streamlit (Python)
- **Backend Logic**: Snowpark Python, Boto3
- **AI**: Snowflake Cortex (Text/Sentiment), OpenAI GPT-4 Vision (via wrapper)

## Setup Instructions

### 1. Database Setup
1. Log in to your Snowflake account.
2. Open a generic SQL worksheet.
3. Copy the contents of `schema.sql` and run all commands to set up tables, views, and sample data.
4. Ensure your user has permissions to create databases and tasks.

### 2. Environment Configuration
1. Rename `.env.example` to `.env`.
2. Fill in your Snowflake credentials and OpenAI API key.
   ```
   SNOWFLAKE_ACCOUNT=...
   SNOWFLAKE_USER=...
   ...
   ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run app.py
```

## Usage Flow
1. **Login**: Use `john@example.com` (User) or `raj@example.com` (Inspector).
2. **Dashboard**: View your properties.
3. **Add Property**: Create a new property entry.
4. **Inspection**: Use the Wizard to upload images and get AI analysis.
5. **Report**: View the detailed risk score and executive summary.
6. **Inspector Mode**: Switch to Inspector user to cross-check AI findings.

## Project Structure
- `app.py`: Main entry point (Login).
- `pages/`: Individual application pages.
- `utils/`: Helper modules for DB, AI, and UI.
- `schema.sql`: Database definitions.

## License
MIT
