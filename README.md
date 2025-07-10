# MHL Logistics Management System

A comprehensive Django-based logistics management system for handling invoices, profit reports, and data import/export operations.

## Features

### Core Functionality
- **Multi-language Support**: Full Arabic (RTL) and English support
- **Modern UI**: Bootstrap 5 with dark/light theme toggle
- **Responsive Design**: Mobile-friendly interface
- **User Management**: Role-based access control (Admin/Regular users)

### Invoice Management
- Create, edit, delete, and view invoices
- Advanced search and filtering
- Import from JSON/Excel files
- Export to JSON/Excel formats
- Invoice comparison and validation
- Batch import tracking

### Reports & Analytics
- Profit and loss reports
- Revenue analysis
- Customer analytics
- Report templates
- Interactive dashboard with charts

### Data Import/Export
- JSON file import/export
- Excel file import/export
- Data validation and error handling
- Comparison with existing records
- Batch processing with detailed logs

## Technology Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: Bootstrap 5, HTML5, CSS3, Vanilla JavaScript
- **File Processing**: pandas, openpyxl
- **Authentication**: Django built-in auth system

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Development Setup

1. **Clone and navigate to the project**:
   ```bash
   cd "/Users/nafa7/Documents/MHL project/MHL_aws"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Create initial data** (optional - includes sample invoices):
   ```bash
   python manage.py setup_initial_data --with-sample-data
   ```

5. **Start development server**:
   ```bash
   python manage.py runserver
   ```

6. **Access the application**:
   - URL: http://localhost:8000
   - Admin login: `admin` / `admin123`
   - Regular user: `user1` / `user123`

### Production Setup

1. **Configure environment variables**:
   ```bash
   cp .env.production .env
   # Edit .env with your production settings
   ```

2. **Set up PostgreSQL**:
   ```bash
   # Update .env file:
   USE_POSTGRESQL=True
   DB_NAME=logistics_production
   DB_USER=your_db_user
   DB_PASSWORD=your_secure_password
   ```

3. **Run production migrations**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

## Project Structure

```
MHL_aws/
├── core/                   # Core app (dashboard, user profiles)
├── accounts/               # User authentication and management
├── invoices/               # Invoice CRUD and import/export
├── reports/                # Profit reports and analytics
├── scripts/                # Utility scripts (import/export)
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
├── data/                   # Import/export files
├── logs/                   # Application logs
└── logistics_project/      # Django project settings
```

## Key Features Explained

### Invoice Import System
- Supports JSON and Excel file formats
- Flexible field mapping (handles various column names)
- Data validation and cleaning
- Duplicate detection and comparison
- Detailed error reporting and logging

### Multi-language Support
- Full internationalization (i18n) support
- Arabic RTL layout support
- Language switching in UI
- Localized date/number formats

### Security Features
- CSRF protection
- XSS prevention
- Input validation and sanitization
- Secure file upload handling
- Role-based access control

### User Interface
- Modern, responsive design
- Dark/light theme toggle
- Collapsible sidebar with "Menu" text
- Professional data tables with sorting/filtering
- Toast notifications and alerts

## Usage Examples

### Importing Invoices

1. **JSON Format**:
   ```json
   [
     {
       "invoice_number": "INV-2024-001",
       "customer_name": "ABC Company",
       "invoice_date": "2024-01-15",
       "total_amount": 1500.00,
       "status": "pending"
     }
   ]
   ```

2. **Excel Format**:
   - Columns: invoice_number, customer_name, invoice_date, total_amount, status
   - Flexible column naming (e.g., "Invoice #", "Customer", "Amount", etc.)

### Creating Reports
1. Navigate to Reports → Profit Analysis
2. Click "Create New Report"
3. Set date range and report type
4. Choose to auto-populate from invoices or enter manually
5. Review and finalize the report

## Management Commands

- `setup_initial_data`: Create initial company and admin user
- `setup_initial_data --with-sample-data`: Include sample invoices

## Configuration

### Environment Variables (.env)
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `USE_POSTGRESQL`: Use PostgreSQL instead of SQLite
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database credentials

### Database Options
- **Development**: SQLite (default)
- **Production**: PostgreSQL (recommended)

## Support

For issues or questions, please check the application logs in the `logs/` directory or contact the development team.

## License

This project is proprietary software developed for MHL Logistics.# test_mhl
