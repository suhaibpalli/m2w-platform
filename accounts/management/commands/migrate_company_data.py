from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Company
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Migrate existing company data to new structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        companies = Company.objects.all()
        total_companies = companies.count()
        updated_count = 0
        
        self.stdout.write(f'Found {total_companies} companies to process...')
        
        with transaction.atomic():
            for company in companies:
                changes_made = False
                
                # Convert old 'role' field to 'company_types'
                if hasattr(company, 'role') and company.role:
                    if not company.company_types:  # Only if not already set
                        if company.role == 'vendor':
                            company.company_types = ['seller', 'manufacturer']
                        elif company.role == 'business_buyer':
                            company.company_types = ['buyer']
                        elif company.role == 'consumer_buyer':
                            company.company_types = ['buyer']
                        else:
                            company.company_types = ['other']
                        changes_made = True
                        self.stdout.write(f'  - Converted role "{company.role}" to company_types: {company.company_types}')
                
                # Set default sectors if empty
                if not company.sectors:
                    # Try to infer from industries if they exist
                    if company.industries.exists():
                        industry_names = [ind.name.lower() for ind in company.industries.all()]
                        sectors = []
                        if any('metal' in name for name in industry_names):
                            sectors.append('metal')
                        if any('wood' in name for name in industry_names):
                            sectors.append('wood')
                        if any('plastic' in name for name in industry_names):
                            sectors.append('plastic')
                        if any('tech' in name or 'technology' in name for name in industry_names):
                            sectors.append('technology')
                        if any('machine' in name for name in industry_names):
                            sectors.append('machinery')
                        
                        if sectors:
                            company.sectors = sectors
                        else:
                            company.sectors = ['other']
                    else:
                        company.sectors = ['other']
                    changes_made = True
                    self.stdout.write(f'  - Set default sectors: {company.sectors}')
                
                # Set contact_person_name if empty
                if not company.contact_person_name:
                    # Try to use the user's first/last name, or email username
                    if company.user.first_name and company.user.last_name:
                        company.contact_person_name = f"{company.user.first_name} {company.user.last_name}"
                    elif company.user.first_name:
                        company.contact_person_name = company.user.first_name
                    else:
                        # Use part of email as fallback
                        email_username = company.user.email.split('@')[0] if company.user.email else company.user.username
                        company.contact_person_name = email_username.replace('.', ' ').replace('_', ' ').title()
                    changes_made = True
                    self.stdout.write(f'  - Set contact person name: {company.contact_person_name}')
                
                # Set contact_email if empty
                if not company.contact_email:
                    company.contact_email = company.user.email
                    changes_made = True
                    self.stdout.write(f'  - Set contact email: {company.contact_email}')
                
                # Set default company_address if empty
                if not company.company_address:
                    if company.country_of_registration:
                        company.company_address = f"Address not specified, {company.country_of_registration}"
                    else:
                        company.company_address = "Address not specified"
                    changes_made = True
                    self.stdout.write(f'  - Set default address: {company.company_address}')
                
                # Migrate registration_number to cr_number if needed
                if hasattr(company, 'registration_number') and company.registration_number and not company.cr_number:
                    company.cr_number = company.registration_number
                    changes_made = True
                    self.stdout.write(f'  - Migrated registration number: {company.cr_number}')
                
                # Set default contact_phone if empty
                if not company.contact_phone:
                    company.contact_phone = "Not provided"
                    changes_made = True
                    self.stdout.write(f'  - Set default phone: {company.contact_phone}')
                
                # Save the company if changes were made
                if changes_made:
                    if not dry_run:
                        company.save()
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Updated company: {company.company_name}'))
                else:
                    self.stdout.write(f'- No changes needed for: {company.company_name}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN COMPLETE - Would have updated {updated_count} companies'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} out of {total_companies} companies'))
