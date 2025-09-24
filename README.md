# Python Data Science Template

A structured template for Python data science projects with PostgreSQL integration, designed for reproducible and organized data analysis workflows.

## Features

- **Database Integration**: PostgreSQL connectivity with aiosql for SQL query management
- **Environment Management**: Poetry for dependency management and virtual environments
- **Notebook Support**: Jupyter notebooks with custom helpers
- **Organized Structure**: Clear separation of utilities, functions, and SQL queries
- **Environment Variables**: Secure configuration management with `.env` files
- **Code Quality**: Configured for pytest and ruff

## Project Structure

```
├── src/
│   ├── python/
│   │   ├── functions/          # Custom analysis functions
│   │   └── utils/              # Database connections, helpers
│   └── sql/
│       ├── ddl_statements/     # Data definition language
│       └── transactional_sql/  # Queries and analysis SQL
├── notebooks/                  # Jupyter notebooks
├── pyproject.toml             # Poetry configuration
└── .env.template              # Environment variables template
```

## Setup

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd python_data_science_template
   poetry install
   ```

2. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your database credentials
   ```

3. **Database configuration** (`.env`):
   ```
   POSTGRES_HOST=localhost
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB_NAME=your_database
   POSTGRES_PORT=5432
   ```

## Usage

### Database Connection

```python
from src.python.utils import connect_to_db, get_queries

# Connect to database
conn = connect_to_db()

# Load SQL queries from files
queries = get_queries()
```

### Jupyter Notebooks

Start Jupyter with project configuration:
```bash
poetry run nb
```

Or manually:
```bash
poetry run jupyter notebook --notebook-dir=notebooks
```

Or make poetry kernel available in Jupyter for usage within VSCode:
```bash
poetry run ipython kernel install --user --name=python_data_science_template
```

### Utilities

The template includes useful utilities:

- **Database helpers**: Connection management and query loading
- **Date utilities**: Generate date series for analysis
- **Notebook helpers**: Custom Jupyter configuration

## Development

- **Testing**: `pytest` (configure as needed)
- **Linting**: `ruff` (configure as needed)
- **SQL Management**: Use `aiosql` for organizing SQL queries in separate files

## Dependencies

- **Data**: pandas, openpyxl
- **Database**: psycopg2, aiosql
- **Environment**: python-dotenv
- **Notebooks**: jupyter, notebook, ipykernel

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This is a template repository. Fork it and adapt it to your specific data science needs.