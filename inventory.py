import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import shutil
from datetime import datetime

# File paths
PRODUCT_DETAILS_FILE = "D:/Sri Divyam Inventory Application/Data Base/product_details.xlsx"
MASTER_DATA_FILE = "D:/Sri Divyam Inventory Application/Data Base/master_data.xlsx"
INVENTORY_CATALOG_FILE = "D:/Sri Divyam Inventory Application/Data Base/inventory_catalog.xlsx"
data_base_folder = "D:/Sri Divyam Inventory Application/Data Base"
backup_folder = "D:/Sri Divyam Inventory Application/backup"
backup_2_folder = "D:/Sri Divyam Inventory Application/backup_2"

# List of files to be copied
files_to_copy = [
    "product_details.xlsx",
    "master_data.xlsx",
    "inventory_catalog.xlsx"
]

def create_folder_if_not_exists(folder_path):
    """Create a folder if it doesn't exist."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
def copy_files():
    """Copy the files from the Data Base folder to backup and backup_2 folders."""
    create_folder_if_not_exists(backup_folder)
    create_folder_if_not_exists(backup_2_folder)

    for file_name in files_to_copy:
        src_file = os.path.join(data_base_folder, file_name)
        
        # Ensure the file exists before copying
        if os.path.exists(src_file):
            # Copy to backup folder
            shutil.copy(src_file, os.path.join(backup_folder, file_name))
            # Copy to backup_2 folder
            shutil.copy(src_file, os.path.join(backup_2_folder, file_name))
            print(f"Copied {file_name} to backup and backup_2 folders.")
        else:
            print(f"{file_name} does not exist in the Data Base folder.")

# Helper Functions
def load_or_create_file(file_path, columns):
    """Load an Excel file or create one with specified columns if it doesn't exist."""
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        for column in columns:
            if column not in df.columns:
                df[column] = None
        return df
    else:
        df = pd.DataFrame(columns=columns)
        save_to_file(file_path, df)  # Save empty DataFrame if file doesn't exist
        return df

def save_to_file(file_path, df):
    """Save the DataFrame to the specified file path and also to a backup location."""
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)

def generate_product_id(existing_ids):
    """Generate a unique product ID in the format 01, 02, 03."""
    if existing_ids.empty:
        return 1
    last_id = max(existing_ids)
    next_id = last_id + 1
    return next_id

def validate_product_name(product_name, product_details):
    """Check if the product name is valid and unique."""
    if product_name.strip() == "":
        return "empty"
    if product_name.lower() in product_details["Product Name"].str.lower().values:
        return "exists"
    return "valid"

def add_new_product(product_name, product_details):
    """Add a new product to the product details DataFrame."""
    product_name_lower = product_name.strip().lower()
    new_id = generate_product_id(product_details["Product ID"].fillna(0).astype(int))
    
    new_product = {
        "Product Name": product_name_lower,
        "Product ID": new_id
    }
    product_details = pd.concat([product_details, pd.DataFrame([new_product])], ignore_index=True)
    save_to_file(PRODUCT_DETAILS_FILE, product_details)
    return new_id

def search_product_in_details(search_input, search_by, product_details):
    """Search for a product by name or ID in product_details.xlsx."""
    if search_by == "Product Name":
        return product_details[product_details["Product Name"].str.lower() == search_input.lower()]
    elif search_by == "Product ID":
        return product_details[product_details["Product ID"].astype(int) == int(search_input)]
    return pd.DataFrame()

def search_product_in_master(search_input, search_by, master_data):
    """Search for a product by name or ID in master_data."""
    if search_by == "Product Name":
        return master_data[master_data["Product ID"].astype(int) == int(search_input)]
    elif search_by == "Product ID":
        return master_data[master_data["Product ID"].astype(int) == int(search_input)]
    return pd.DataFrame()

def log_inventory_transaction(product_id, quantity, total_cost, purchase_date, inventory_catalog, master_data):
    """Log the transaction in the inventory catalog with timestamp and update master_data."""
    timestamp = datetime.now()  # Get the current timestamp
    transaction = {
        "Product ID": product_id,
        "Quantity Added": quantity,  # Quantity should be negative for factory usage
        "Total Cost": total_cost,
        "Purchase Date": purchase_date,
        "Timestamp": timestamp
    }
    
    # Add transaction to inventory catalog
    inventory_catalog = pd.concat([inventory_catalog, pd.DataFrame([transaction]).dropna(axis=1, how='all')], ignore_index=True)
    
    # Save the updated inventory catalog
    save_to_file(INVENTORY_CATALOG_FILE, inventory_catalog)

    # Retrieve product name from product_details
    product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
    product_name = product_details.loc[product_details["Product ID"] == product_id, "Product Name"].values[0]

    # Update master_data
    product_in_master = master_data[master_data["Product ID"] == product_id]
    
    if product_in_master.empty:
        # If product is not found, create a new entry in master_data (if needed)
        avg_price = total_cost / quantity  # Average price calculation
        new_entry = {
            "Product ID": product_id,
            "Total Quantity": quantity,
            "Average Price": avg_price,
            "Highest Price": avg_price,
            "Latest Price": avg_price,
            "Latest Purchase Date": pd.to_datetime(purchase_date)  # Convert to datetime
        }
        master_data = pd.concat([master_data, pd.DataFrame([new_entry]).dropna(axis=1, how='all')], ignore_index=True)
    else:
        # If product exists in master_data, update the fields
        idx = product_in_master.index[0]
        
        # Get existing data from master_data
        old_quantity = master_data.at[idx, "Total Quantity"]
        old_avg_price = master_data.at[idx, "Average Price"]
        old_highest_price = master_data.at[idx, "Highest Price"]
        old_latest_price = master_data.at[idx, "Latest Price"]
        old_latest_date = master_data.at[idx, "Latest Purchase Date"]

        # Calculate new average price, total quantity, and highest price
        new_avg_price = (old_quantity * old_avg_price + quantity * (total_cost / quantity)) / (old_quantity + quantity)
        new_highest_price = max(old_highest_price, total_cost / quantity)

        # Update the row in master_data
        master_data.at[idx, "Total Quantity"] = old_quantity + quantity
        master_data.at[idx, "Average Price"] = new_avg_price
        master_data.at[idx, "Highest Price"] = new_highest_price
        master_data.at[idx, "Latest Price"] = total_cost / quantity
        master_data.at[idx, "Latest Purchase Date"] = pd.to_datetime(purchase_date)  # Convert to datetime

    # Save the updated master_data
    save_to_file(MASTER_DATA_FILE, master_data)
   


def rename_product(product_id, new_name, product_details):
    """Rename an existing product in the product details DataFrame."""
    product_id = int(product_id)  # Ensure product_id is treated as integer
    # Search for the product by ID
    product = product_details[product_details["Product ID"] == product_id]
    
    if product.empty:
        return "Product not found"
    
    # Check if new name already exists
    if new_name.strip().lower() in product_details["Product Name"].str.lower().values:
        return "Product name already exists"
    
    # Update the product name
    product_details.loc[product_details["Product ID"] == product_id, "Product Name"] = new_name.strip().lower()
    save_to_file(PRODUCT_DETAILS_FILE, product_details)
    return "Product renamed successfully"

# Streamlit Interface Functions
def handle_new_product():
    """Handle adding a new product through the Streamlit interface."""
    st.title("Add New Product")
    product_name = st.text_input("Enter Product Name:")
    add_button = st.button("Add Product")
    
    product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
    
    if add_button:
        validation_result = validate_product_name(product_name, product_details)
        if validation_result == "empty":
            st.warning("Product name cannot be empty!")
        elif validation_result == "exists":
            st.warning(f"The product '{product_name}' already exists!")
        else:
            new_id = add_new_product(product_name, product_details)
            st.success(f"Product '{product_name}' added successfully with ID {new_id}!")

def handle_add_quantity():
    """Handle adding quantity to an existing product."""
    st.title("Add Quantity to an Existing Product")

    # Search for a product either by Name or ID
    search_by = st.radio("Search By", ["Product Name", "Product ID"])
    search_input = st.text_input(f"Enter {search_by}:")

    if search_input:
        # Load product details
        product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
        product = search_product_in_details(search_input, search_by, product_details)

        if product.empty:
            st.error("Product not found. Please try again.")
        else:
            product_details_row = product.iloc[0]
            st.write(f"**Product Name:** {product_details_row['Product Name']}")
            st.write(f"**Product ID:** {product_details_row['Product ID']}")

            # Now load the master data to fetch available quantity
            master_data = load_or_create_file(MASTER_DATA_FILE, [
                "Product ID", "Total Quantity", 
                "Average Price", "Latest Price", "Highest Price", 
                "Lowest Price", "Latest Purchase Date"
            ])

            # Search for the product in master data
            product_in_master = master_data[master_data["Product ID"] == product_details_row["Product ID"]]

            if not product_in_master.empty:
                available_quantity = product_in_master["Total Quantity"].values[0]
                st.write(f"**Available Quantity:** {available_quantity} units")

            # Form to enter quantity and cost
            with st.form(key="quantity_form"):
                quantity = st.number_input("Enter Quantity to Add:", min_value=0.01, format="%.2f")
                total_cost = st.number_input("Enter Total Cost (₹):", min_value=0.01, format="%.2f")
                purchase_date = st.date_input("Purchase Date:", value=datetime.today())
                submit_button = st.form_submit_button(label="Add Quantity")

                if submit_button:
                    if quantity <= 0 or total_cost <= 0:
                        st.warning("Quantity and Total Cost must be greater than zero.")
                    else:
                        # Log the transaction and update master_data
                        inventory_catalog = load_or_create_file(INVENTORY_CATALOG_FILE, [
                            "Product ID", "Quantity Added", "Total Cost", "Purchase Date", "Timestamp"
                        ])
                        log_inventory_transaction(product_details_row["Product ID"], quantity, total_cost, purchase_date, inventory_catalog, master_data)

                        st.success(f"Successfully added {quantity} units to {product_details_row['Product Name']}!")
def handle_search_product():
    """Handle searching a product and displaying the master data."""
    st.title("Search a Product")
    
    search_by = st.radio("Search By", ["Product Name", "Product ID"])
    search_input = st.text_input(f"Enter {search_by}:")

    if search_input:
        # Load product details
        product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
        
        product_id = None  # Initialize product_id
        product_name = None  # Initialize product_name

        if search_by == "Product Name":
            # Search for the product by name (case-insensitive)
            product = search_product_in_details(search_input, search_by, product_details)
            if product.empty:
                st.error(f"Product with name '{search_input}' not found.")
            else:
                product_id = product["Product ID"].values[0]  # Get the Product ID from product details
                # Displaying product details correctly
                st.write(f"**Product Name:** {product['Product Name'].iloc[0]}")
                st.write(f"**Product ID:** {product_id}")
        else:
            # If searching by Product ID, ensure input is an integer
            product_id = int(search_input.strip())
            st.write(f"**Product ID:** {product_id}")

        if product_id is not None:
            # Now search for the product in master_data using the ID
            master_data = load_or_create_file(MASTER_DATA_FILE, [
                "Product ID", "Total Quantity", 
                "Average Price", "Latest Price", "Highest Price", 
                "Lowest Price", "Latest Purchase Date"
            ])
            
            product_in_master = master_data[master_data["Product ID"] == product_id]
            if product_in_master.empty:
                st.error(f"Product with ID '{product_id}' not found in master data.")
            else:
                # Retrieve product name from product_details using product_id
                product_name = product_details[product_details["Product ID"] == product_id]["Product Name"].values[0]
                
                # Display product name along with the details from master_data
                st.write(f"**Product Name:** {product_name}")
                st.write("### Product Details from Master Data")
                st.write(product_in_master)

def handle_rename_product():
    """Handle renaming an existing product through the Streamlit interface."""
    st.title("Rename an Existing Product")

    # Search for a product either by Name or ID
    search_by = st.radio("Search By", ["Product Name", "Product ID"])
    product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
    
    if search_by == "Product Name":
        product_names = product_details["Product Name"].tolist()
        search_input = st.selectbox("Select Product Name", product_names)
    else:
        product_ids = product_details["Product ID"].tolist()
        search_input = st.selectbox("Select Product ID", product_ids)
    
    if search_input:
        product = search_product_in_details(search_input, search_by, product_details)
        
        if product.empty:
            st.error("Product not found. Please try again.")
        else:
            product_details_row = product.iloc[0]
            st.write(f"**Product Name:** {product_details_row['Product Name']}")
            st.write(f"**Product ID:** {product_details_row['Product ID']}")

            # Form to enter new name
            new_name = st.text_input("Enter New Product Name:", value=product_details_row['Product Name'])
            submit_button = st.button("Rename Product")
            
            if submit_button:
                # Validate the new name
                if new_name.strip() == "":
                    st.warning("Product name cannot be empty!")
                else:
                    # Rename the product in the details
                    result = rename_product(product_details_row["Product ID"], new_name, product_details)
                    if result == "Product renamed successfully":
                        st.success(f"Product has been renamed to {new_name} successfully!")
                    else:
                        st.warning(result)
def load_or_create_file(file_path, columns):
    """Load an Excel file or create one with specified columns if it doesn't exist."""
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        for column in columns:
            if column not in df.columns:
                df[column] = None
        return df
    else:
        df = pd.DataFrame(columns=columns)
        save_to_file(file_path, df)  # Save empty DataFrame if file doesn't exist
        return df

def save_to_file(file_path, df):
    """Save the DataFrame to the specified file path."""
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)

def add_logo():
    """Display a logo in the top right corner."""
    logo_path = r"D:\Sri Divyam Inventory Application\photo\sridhivyum logo.jpg" 
    # Use columns to position the logo
    col1, col2 = st.columns([8, 1])  # Adjust column widths
    with col1:
        st.empty()  # Leave the left side empty
    with col2:
        st.image(logo_path, use_container_width=True)  # Display the logo in the right column
def handle_factory_usage():
    """Handle factory usage and update inventory."""
    st.title("Factory Usage - Deduct Inventory")
    
    # Ask user to search for a product by Name or ID
    search_by = st.radio("Search By", ["Product Name", "Product ID"])
    search_input = st.text_input(f"Enter {search_by}:")
    
    if search_input:
        # Load product details
        product_details = load_or_create_file(PRODUCT_DETAILS_FILE, ["Product Name", "Product ID"])
        product = search_product_in_details(search_input, search_by, product_details)
        
        if product.empty:
            st.error("Product not found. Please try again.")
        else:
            product_details_row = product.iloc[0]
            st.write(f"**Product Name:** {product_details_row['Product Name']}")
            st.write(f"**Product ID:** {product_details_row['Product ID']}")
            
            # Load master data to check current stock
            master_data = load_or_create_file(MASTER_DATA_FILE, [
                "Product ID", "Total Quantity", 
                "Average Price", "Latest Price", "Highest Price", 
                "Lowest Price", "Latest Purchase Date"
            ])
            
            product_in_master = master_data[master_data["Product ID"] == product_details_row["Product ID"]]

            if not product_in_master.empty:
                available_quantity = product_in_master["Total Quantity"].values[0]
                st.write(f"**Available Quantity:** {available_quantity} units")
            
            # Form to input quantity used and the date
            with st.form(key="factory_usage_form"):
                quantity_used = st.number_input("Enter Quantity Used:", min_value=0.01, format="%.2f")
                usage_date = st.date_input("Usage Date:", value=datetime.today())
                submit_button = st.form_submit_button(label="Deduct Quantity")

                if submit_button:
                    if quantity_used <= 0:
                        st.warning("Quantity used must be greater than zero.")
                    elif quantity_used > available_quantity:
                        st.warning("Insufficient quantity in stock!")
                    else:
                        # Log the factory usage and update master_data
                        inventory_catalog = load_or_create_file(INVENTORY_CATALOG_FILE, [
                            "Product ID", "Quantity Added", "Total Cost", "Purchase Date", "Timestamp"
                        ])
                        
                        # Calculate the cost based on available price in master_data
                        avg_price = product_in_master["Average Price"].values[0] if not product_in_master.empty else 0
                        total_cost = quantity_used * avg_price
                        
                        # Log the transaction as a negative quantity for usage
                        log_inventory_transaction(product_details_row["Product ID"], -quantity_used, total_cost, usage_date, inventory_catalog, master_data)
                        
                        st.success(f"Successfully deducted {quantity_used} units from {product_details_row['Product Name']} inventory.")



# Main App
def main():
    add_logo()
    # Sidebar options using a radio button
    option = st.sidebar.radio("Choose an action", ["Add New Product", "Add Quantity", "Factory Usage", "Search a Product", "Rename Product"])

    if option == "Add New Product":
        handle_new_product()
        copy_files()
    elif option == "Add Quantity":
        handle_add_quantity()
        copy_files()
    elif option == "Factory Usage":
        handle_factory_usage()
        copy_files()  # This will be the new function
    elif option == "Search a Product":
        handle_search_product()
        copy_files()
    elif option == "Rename Product":
        handle_rename_product()
        copy_files()

if __name__ == "__main__":
    main()
