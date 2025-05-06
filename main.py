import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import csv
from generate_android_pass import generate_android_pass


# Connect to the database and get event names
def get_event_names():
    conn = sqlite3.connect("event_tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Events")
    events = [row[0] for row in cursor.fetchall()]
    conn.close()
    return events


# Add new event to the database
def add_new_event():
    new_event = event_name_entry.get().strip()
    if new_event:
        conn = sqlite3.connect("event_tickets.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Events (name) VALUES (?)", (new_event,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Event '{new_event}' added.")
        refresh_event_list()
        event_var.set(new_event)


def refresh_event_list():
    event_menu['values'] = get_event_names()


# Load CSV and display data
def load_csv():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        return

    selected_event = event_var.get()
    if not selected_event:
        messagebox.showerror("Error", "Please select or create an event first.")
        return

    # Get or create event_id
    conn = sqlite3.connect("event_tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT event_id FROM Events WHERE name = ?", (selected_event,))
    event = cursor.fetchone()
    if event:
        event_id = event[0]
    else:
        cursor.execute("INSERT INTO Events (name) VALUES (?)", (selected_event,))
        conn.commit()
        cursor.execute("SELECT event_id FROM Events WHERE name = ?", (selected_event,))
        event_id = cursor.fetchone()[0]

    with open(file_path, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        required_fields = ['name', 'phone', 'email']

        for field in required_fields:
            if field not in reader.fieldnames:
                messagebox.showerror("CSV Error", f"Missing column: {field}")
                conn.close()
                return

        for row in reader:
            name = row['name']
            phone = row['phone']
            email = row.get('email', '')

            cursor.execute("INSERT INTO Attendees (name, phone, email) VALUES (?, ?, ?)", (name, phone, email))
            attendee_id = cursor.lastrowid
            barcode = f"{name[:3].upper()}-{event_id}-{attendee_id}"
            cursor.execute("""INSERT INTO Tickets 
                              (attendee_id, event_id, ticket_type, barcode, pass_design) 
                              VALUES (?, ?, 'Normal', ?, 'default')""", (attendee_id, event_id, barcode))
            tree.insert("", "end", values=(name, phone, email, "Normal"))

    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "CSV imported successfully.")


# Save changes to ticket types
def save_changes():
    conn = sqlite3.connect("event_tickets.db")
    cursor = conn.cursor()
    for item in tree.get_children():
        values = tree.item(item)['values']
        name, phone, email, ticket_type = values
        cursor.execute("""
            SELECT a.attendee_id, t.ticket_id FROM Attendees a
            JOIN Tickets t ON a.attendee_id = t.attendee_id
            WHERE a.name = ? AND a.phone = ?
        """, (name, phone))
        result = cursor.fetchone()
        if result:
            attendee_id, ticket_id = result
            cursor.execute("UPDATE Tickets SET ticket_type = ? WHERE ticket_id = ?", (ticket_type, ticket_id))
    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Ticket types updated.")


# Handle ticket type changes
def on_double_click(event):
    item = tree.identify_row(event.y)
    if item:
        col = tree.identify_column(event.x)
        if col == '#4':  # ticket_type column
            x, y, width, height = tree.bbox(item, col)
            entry_popup = ttk.Combobox(root, values=["VVIP", "VIP", "Normal", "Staff"])
            entry_popup.place(x=x + tree.winfo_rootx() - root.winfo_rootx(),
                              y=y + tree.winfo_rooty() - root.winfo_rooty(),
                              width=width, height=height)
            entry_popup.focus()
            entry_popup.set(tree.item(item, 'values')[3])

            def on_select(event):
                new_value = entry_popup.get()
                values = list(tree.item(item, 'values'))
                values[3] = new_value
                tree.item(item, values=values)
                entry_popup.destroy()

            entry_popup.bind("<<ComboboxSelected>>", on_select)
            entry_popup.bind("<FocusOut>", lambda e: entry_popup.destroy())


def send_passes():
    selected_event = event_var.get()
    if not selected_event:
        messagebox.showerror("Error", "Please select an event first")
        return

    for item in tree.get_children():
        name, phone, email, ticket_type = tree.item(item)["values"]

        conn = sqlite3.connect("event_tickets.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT barcode FROM Tickets t
            JOIN Attendees a ON t.attendee_id = a.attendee_id
            JOIN EVENTS e ON t.event_id = e.event_id
            WHERE a.name = ? AND a.phone = ? AND e.name = ?
        """, (name, phone, selected_event))
        result = cursor.fetchone()
        conn.close()

        if not result:
            messagebox.showerror("Error", f"No barcode found for {name}")
            continue

        barcode = result[0]
        generate_android_pass(name, selected_event, ticket_type, barcode, email, phone)

    messagebox.showinfo("Success", "All passes are generated and emailed!")


# Initialize window
root = tk.Tk()
root.title("Event Ticket Manager")

# Event selection
event_frame = tk.Frame(root)
event_frame.pack(pady=10)

tk.Label(event_frame, text="Event Name:").pack(side=tk.LEFT)
event_var = tk.StringVar()
event_menu = ttk.Combobox(event_frame, textvariable=event_var, values=get_event_names(), width=30)
event_menu.pack(side=tk.LEFT, padx=5)

event_name_entry = tk.Entry(event_frame)
event_name_entry.pack(side=tk.LEFT)
tk.Button(event_frame, text="+ Add New Event", command=add_new_event).pack(side=tk.LEFT, padx=5)

# CSV import button
tk.Button(root, text="Import Attendee CSV", command=load_csv).pack(pady=5)

# Table for attendees
columns = ("name", "phone", "email", "ticket_type")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col.capitalize())
    tree.column(col, width=150)
tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
tree.bind("<Double-1>", on_double_click)

# Save changes button
tk.Button(root, text="Save Changes", command=save_changes).pack(pady=5)
# Send Button
tk.Button(root, text="Send Passes", command=send_passes).pack(pady=5)

root.mainloop()
