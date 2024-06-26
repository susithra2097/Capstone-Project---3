import streamlit as st
from streamlit_option_menu import option_menu
import easyocr
from PIL import Image
import pandas as pd
import numpy as np
import re
import io
import sqlite3

# Function to create the database table if it doesn't exist
def create_table_if_not_exists(cursor):
    create_table_query = '''CREATE TABLE IF NOT EXISTS bizcard_details(
        name varchar(225),
        designation varchar(225),
        company_name varchar(225),
        contact varchar(225),
        email varchar(225),
        website text,
        address text,
        pincode varchar(225),
        image text
    )'''
    cursor.execute(create_table_query)

# Function to extract text from the image
def image_to_text(path):
    input_img = Image.open(path)
    image_array = np.array(input_img)
    reader = easyocr.Reader(['en'])
    text = reader.readtext(image_array, detail=0)
    return text, input_img

# Function to extract relevant information from the extracted text
def extracted_text(texts):
    extracted_dict = {"NAME": [], "DESIGNATION": [], "COMPANY_NAME": [], "CONTACT": [], "EMAIL": [], "WEBSITE": [],
                      "ADDRESS": [], "PINCODE": []}

    extracted_dict["NAME"].append(texts[0])
    extracted_dict["DESIGNATION"].append(texts[1])

    for i in range(2, len(texts)):
        if texts[i].startswith("+") or (texts[i].replace("-", "").isdigit() and '-' in texts[i]):
            extracted_dict["CONTACT"].append(texts[i])
        elif "@" in texts[i] and ".com" in texts[i]:
            extracted_dict["EMAIL"].append(texts[i])
        elif "WWW" in texts[i] or "www" in texts[i] or "Www" in texts[i] or "wWw" in texts[i] or "wwW" in texts[i]:
            small = texts[i].lower()
            extracted_dict["WEBSITE"].append(small)
        elif "Tamil Nadu" in texts[i] or "TamilNadu" in texts[i] or texts[i].isdigit():
            extracted_dict["PINCODE"].append(texts[i])
        elif re.match(r'^[A-Za-z]', texts[i]):
            extracted_dict["COMPANY_NAME"].append(texts[i])
        else:
            remove_colon = re.sub(r'[,;]', '', texts[i])
            extracted_dict["ADDRESS"].append(remove_colon)

    for key, value in extracted_dict.items():
        if len(value) > 0:
            concatenate = " ".join(value)
            extracted_dict[key] = [concatenate]
        else:
            value = "NA"
            extracted_dict[key] = [value]

    return extracted_dict

# Streamlit part
st.set_page_config(layout="wide")
st.title("Bizcard: Business Card Data Extraction with OCR")

with st.sidebar:
    select_option = option_menu("Main Menu", ["Home", "Upload & Save", "Preview","Modify", "Delete"])

# Database connection
try:
    mydb = sqlite3.connect("bizcardx.db")
    cursor = mydb.cursor()
    create_table_if_not_exists(cursor)
except sqlite3.Error as e:
    st.error(f"Error: {e}")

# Handling different menu options
if select_option == "Home":
    st.markdown("### :red[**Technologies Used :**] Python, easy OCR, Streamlit, SQL, Pandas")
    st.write("#### :green[**About :**] Bizcard is a Python application designed to extract information from business cards.")
    st.write('The main purpose of Bizcard is to automate the process of extracting key details from business card images, such as the name, designation, company, contact information, and other relevant data. By leveraging the power of OCR (Optical Character Recognition) provided by EasyOCR, Bizcard is able to extract text from the images.')

    # Add a section for features
    st.write("### :blue[**Features:**]")
    st.write("- Upload and save business card images.")
    st.write("- Extract text from uploaded images using EasyOCR.")
    st.write("- Display extracted information such as name, designation, company, contact details, etc.")
    st.write("- Save extracted data to a SQLite database.")
    st.write("- Modify or delete saved business card entries.")

elif select_option == "Upload & Save":
    img = st.file_uploader("Upload the Image", type=["png", "jpg", "jpeg"])

    if img is not None:
        st.image(img, width=300)

        text_image, input_img = image_to_text(img)

        text_dict = extracted_text(text_image)

        if text_dict:
            st.success("TEXT IS EXTRACTED SUCCESSFULLY")

            df = pd.DataFrame(text_dict)

            # Check if the data already exists in the database
            existing_data = cursor.execute("SELECT * FROM bizcard_details").fetchall()
            existing_data_df = pd.DataFrame(existing_data, columns=["NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE", "ADDRESS", "PINCODE", "IMAGE"])

            duplicate_check_columns = ["NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE", "ADDRESS", "PINCODE"]
            is_duplicate = existing_data_df[duplicate_check_columns].apply(lambda row: row.equals(df[duplicate_check_columns].iloc[0]), axis=1).any()

            if is_duplicate:
                st.error("A business card with the same data already exists in the database.")
            else:
                # Converting Image to Bytes
                Image_bytes = io.BytesIO()
                input_img.save(Image_bytes, format="PNG")
                image_data = Image_bytes.getvalue()

                # Creating Dictionary
                data = {"IMAGE": [image_data]}
                df_1 = pd.DataFrame(data)
                concat_df = pd.concat([df, df_1], axis=1)

                st.dataframe(concat_df)

                button_1 = st.button("Save", use_container_width=True)

                if button_1:
                    try:
                        # Insert Query
                        insert_query = '''INSERT INTO bizcard_details(name, designation, company_name, contact, email, website, address, pincode, image)
                                          VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                        datas = concat_df.values.tolist()[0]
                        cursor.execute(insert_query, datas)
                        mydb.commit()
                        st.success("SAVED SUCCESSFULLY")
                    except sqlite3.Error as e:
                        st.error(f"Error: {e}")


elif select_option == "Modify":
    try:
        # select query
        select_query = "SELECT * FROM bizcard_details"
        cursor.execute(select_query)
        table = cursor.fetchall()
        mydb.commit()
        table_df = pd.DataFrame(table, columns=("NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE",
                                                "ADDRESS", "PINCODE", "IMAGE"))

        col1, col2 = st.columns(2)
        with col1:
            selected_name = st.selectbox("Select the name", table_df["NAME"])

        df_3 = table_df[table_df["NAME"] == selected_name]

        if not df_3.empty:  # Check if df_3 is not empty
            df_4 = df_3.copy()

            # Streamlit UI for modifying data
            col1, col2 = st.columns(2)
            with col1:
                mo_name = st.text_input("Name", df_3["NAME"].iloc[0])
                mo_desi = st.text_input("Designation", df_3["DESIGNATION"].iloc[0])
                mo_com_name = st.text_input("Company_name", df_3["COMPANY_NAME"].iloc[0])
                mo_contact = st.text_input("Contact", df_3["CONTACT"].iloc[0])
                mo_email = st.text_input("Email", df_3["EMAIL"].iloc[0])

                df_4["NAME"] = mo_name
                df_4["DESIGNATION"] = mo_desi
                df_4["COMPANY_NAME"] = mo_com_name
                df_4["CONTACT"] = mo_contact
                df_4["EMAIL"] = mo_email

            with col2:
                mo_website = st.text_input("Website", df_3["WEBSITE"].iloc[0])
                mo_addre = st.text_input("Address", df_3["ADDRESS"].iloc[0])
                mo_pincode = st.text_input("Pincode", df_3["PINCODE"].iloc[0])
                mo_image = st.text_input("Image", df_3["IMAGE"].iloc[0])

                df_4["WEBSITE"] = mo_website
                df_4["ADDRESS"] = mo_addre
                df_4["PINCODE"] = mo_pincode
                df_4["IMAGE"] = mo_image

            st.write("---")
            st.write("### Modify Data")
            st.dataframe(df_4)

            col1, col2 = st.columns(2)
            with col1:
                button_modify = st.button("Modify", use_container_width=True)

            if button_modify:
                try:
                    # Update Query
                    update_query = '''UPDATE bizcard_details SET name=?, designation=?, company_name=?, contact=?, 
                                      email=?, website=?, address=?, pincode=?, image=? WHERE name=?'''
                    # Convert dataframe row to tuple for SQL insertion
                    new_data = tuple(df_4.values.tolist()[0] + [selected_name])
                    cursor.execute(update_query, new_data)
                    mydb.commit()
                    st.success("Modified successfully.")
                except sqlite3.Error as e:
                    st.error(f"Error: {e}")

    except sqlite3.Error as e:
        st.error(f"Error: {e}")

elif select_option == "Preview":
    mydb = sqlite3.connect("bizcardx.db")
    cursor = mydb.cursor()

    #select query
    select_query = "SELECT * FROM bizcard_details"

    cursor.execute(select_query)
    table = cursor.fetchall()
    mydb.commit()

    table_df = pd.DataFrame(table, columns=("NAME", "DESIGNATION", "COMPANY_NAME", "CONTACT", "EMAIL", "WEBSITE",
                                            "ADDRESS", "PINCODE", "IMAGE"))
    st.dataframe(table_df)


elif select_option == "Delete":
    try:
        col1, col2, col3 = st.columns(3)  # Adding another column for email and contact
        with col1:
            select_query = "SELECT NAME FROM bizcard_details"
            cursor.execute(select_query)
            table1 = cursor.fetchall()
            mydb.commit()
            names = [i[0] for i in table1]
            name_select = st.selectbox("Select the name", names)

        with col2:
            select_query = f"SELECT DESIGNATION FROM bizcard_details WHERE NAME ='{name_select}'"
            cursor.execute(select_query)
            table2 = cursor.fetchall()
            mydb.commit()
            designations = [j[0] for j in table2]
            designation_select = st.selectbox("Select the designation", options=designations)

        with col3:
            select_query = f"SELECT EMAIL FROM bizcard_details WHERE NAME ='{name_select}' AND DESIGNATION = '{designation_select}'"
            cursor.execute(select_query)
            table3 = cursor.fetchall()
            mydb.commit()
            emails = [k[0] for k in table3]
            email_select = st.selectbox("Select the email", options=emails)

        if name_select and designation_select and email_select:
            remove = st.button("Delete", use_container_width=True)
            if remove:
                try:
                    cursor.execute(f"DELETE FROM bizcard_details WHERE NAME ='{name_select}' AND DESIGNATION = '{designation_select}' AND EMAIL = '{email_select}'")
                    mydb.commit()
                    st.warning("DELETED")
                except sqlite3.Error as e:
                    st.error(f"Error: {e}")

    except sqlite3.Error as e:
        st.error(f"Error: {e}")
