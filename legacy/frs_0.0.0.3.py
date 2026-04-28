"""
Sistema de Control de Acceso con Reconocimiento Facial para Gimnasio
"""
import os
import csv
import sqlite3
import numpy as np
from datetime import datetime
from PIL import Image, ImageTk
import cv2 as cv
import tkinter as tk
from tkinter import ttk, messagebox

# Constantes
DB_PATH = 'members.db'
SAMPLES_DIR = 'face_samples'
DARK_BG = "#1E1E1E"
LIGHT_BG = "#2D2D30"
ACCENT_COLOR = "#0078D7"
TEXT_COLOR = "#FFFFFF"

# Inicialización del detector y reconocedor facial
try:
    CASC_PATH = cv.data.haarcascades + 'haarcascade_frontalface_default.xml'
except AttributeError:
    CASC_PATH = 'haarcascade_frontalface_default.xml'
face_cascade = cv.CascadeClassifier(CASC_PATH)
recognizer = cv.face.LBPHFaceRecognizer_create()

# Funciones de preparación
def ensure_dirs():
    """Crea directorios necesarios"""
    if not os.path.exists(SAMPLES_DIR):
        os.makedirs(SAMPLES_DIR)

def init_db():
    """Inicializa la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS members (
        membership_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        expiration_date TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()
    ensure_dirs()

def train_recognizer():
    """Entrena el reconocedor facial"""
    images = [os.path.join(SAMPLES_DIR, f) for f in os.listdir(SAMPLES_DIR) 
             if f.lower().endswith(('.png','.jpg','.jpeg'))]
    ids = []
    faces = []
    labels = []
    
    for idx, img_path in enumerate(images):
        img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
        if img is None:
            continue
        faces.append(img)
        labels.append(idx)
        member_id = os.path.splitext(os.path.basename(img_path))[0]
        ids.append(member_id)
    
    if faces:
        recognizer.train(faces, np.array(labels))
    return ids

class CameraCapture:
    """Gestiona la captura de rostros desde la cámara"""
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
    def start(self):
        """Inicia el proceso de captura"""
        # Crear ventana de captura
        self.capture_window = tk.Toplevel(self.parent)
        self.capture_window.title("Captura Facial")
        self.capture_window.configure(bg=DARK_BG)
        self.capture_window.geometry("640x580")  # Altura del recuadro
        
        # Marco para el video
        frame = tk.Frame(self.capture_window, bg=LIGHT_BG, bd=2, relief=tk.GROOVE)
        frame.pack(pady=10, padx=10, fill=tk.X, expand=False)
        #tamaño fijo para el marco video
        frame.config(height=390)  # Altura fija
        
        # Etiqueta para mostrar el video
        self.video_label = tk.Label(frame, bg=LIGHT_BG)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Contenedor para instrucciones y botón
        controls_frame = tk.Frame(self.capture_window, bg=DARK_BG, height=100)
        controls_frame.pack(fill=tk.X, pady=0.01)
        
        # Instrucciones
        self.status = tk.Label(
            controls_frame, 
            text="Posicione su rostro en el centro", 
            bg=DARK_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 10)
        )
        self.status.pack(pady=0.5)
        
        # Botón de captura
        button_frame = tk.Frame(controls_frame, bg=DARK_BG)
        button_frame.pack(pady=1)
        
        self.capture_btn = ttk.Button(
            button_frame,
            text="Capturar",
            command=self.on_capture,
            state="disabled",
            # Hacer el botón más grande y visible
            width=15  # Ancho en caracteres
        )
        self.capture_btn.pack(pady=2)
        
        # Iniciar cámara
        self.cap = cv.VideoCapture(0, cv.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "No se pudo acceder a la cámara")
            self.capture_window.destroy()
            return None
            
        self.update_frame()
        self.parent.wait_window(self.capture_window)
        return self.result
        
    def update_frame(self):
        """Actualiza el fotograma de video"""
        ret, frame = self.cap.read()
        if ret:
            # Espejo y procesamiento
            frame = cv.flip(frame, 1)
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            
            # Guía visual para posicionar rostro
            center_x, center_y = frame.shape[1]//2, frame.shape[0]//2
            cv.rectangle(frame, (center_x-100, center_y-100), 
                        (center_x+100, center_y+100), (255,255,255), 2)
            
            # Detección de rostros
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            
            face_detected = False
            for (x, y, w, h) in faces:
                cv.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Verificar si el rostro está centrado
                if (abs(x + w/2 - center_x) < 50 and 
                    abs(y + h/2 - center_y) < 50 and
                    len(faces) == 1):
                    self.roi = gray[y:y+h, x:x+w]
                    self.status.config(text="Rostro detectado. Puede capturar.")
                    self.capture_btn.config(state="normal")
                    face_detected = True
                    
            if not face_detected:
                self.status.config(text="Centre su rostro en el recuadro")
                self.capture_btn.config(state="disabled")
                
            # Mostrar frame en tkinter
            img = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
        # Continuar si la ventana sigue abierta
        if self.capture_window.winfo_exists():
            self.capture_window.after(10, self.update_frame)
        else:
            self.cap.release()
            
    def on_capture(self):
        """Procesa captura de rostro"""
        self.result = self.roi
        self.capture_window.destroy()
        self.cap.release()

class GymAccessApp:
    """Aplicación principal de control de acceso"""
    def __init__(self, root):
        self.root = root
        self.root.title("GymAccess - Control de Acceso")
        self.root.geometry("700x500")
        self.root.configure(bg=DARK_BG)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Estilos
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 11, "bold"), padding=8)
        style.configure("Accent.TButton", font=("Arial", 11, "bold"))
        
        # Banner superior
        header = tk.Frame(self.root, bg=ACCENT_COLOR, height=80)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, 
            text="Sistema de Control de Acceso", 
            bg=ACCENT_COLOR, 
            fg=TEXT_COLOR,
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        # Contenedor principal
        main_frame = tk.Frame(self.root, bg=DARK_BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Opciones principales (usando grid para dos columnas)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        
        # Tarjeta de registro
        reg_frame = tk.Frame(main_frame, bg=LIGHT_BG, padx=15, pady=15, bd=1, relief=tk.SOLID)
        reg_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        tk.Label(
            reg_frame, 
            text="Registro de Miembros",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))
        
        tk.Label(
            reg_frame, 
            text="👤",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 36)
        ).pack(pady=20)
        
        tk.Label(
            reg_frame, 
            text="Registre nuevos miembros\ncon reconocimiento facial",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            justify=tk.CENTER
        ).pack(pady=10)
        
        ttk.Button(
            reg_frame,
            text="Registrar Miembro",
            command=self.register_member
        ).pack(pady=10)
        
        # Tarjeta de verificación
        verify_frame = tk.Frame(main_frame, bg=LIGHT_BG, padx=15, pady=15, bd=1, relief=tk.SOLID)
        verify_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        tk.Label(
            verify_frame, 
            text="Verificación de Acceso",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))
        
        tk.Label(
            verify_frame, 
            text="🔍",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 36)
        ).pack(pady=20)
        
        tk.Label(
            verify_frame, 
            text="Verifique el acceso de miembros\nmediante reconocimiento facial",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            justify=tk.CENTER
        ).pack(pady=10)
        
        ttk.Button(
            verify_frame,
            text="Verificar Acceso",
            command=self.verify_member
        ).pack(pady=10)
        
        # Tarjeta de edición
        edit_frame = tk.Frame(main_frame, bg=LIGHT_BG, padx=15, pady=15, bd=1, relief=tk.SOLID)
        edit_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        tk.Label(
            edit_frame, 
            text="Edición de Miembros",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))
        
        tk.Label(
            edit_frame, 
            text="     ✏️",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            font=("Arial", 36)
        ).pack(pady=20, anchor='center')
        
        tk.Label(
            edit_frame, 
            text="Actualice datos de miembros\no recapture su rostro",
            bg=LIGHT_BG, 
            fg=TEXT_COLOR,
            justify=tk.CENTER
        ).pack(pady=10)
        
        ttk.Button(
            edit_frame,
            text="Editar Miembro",
            command=self.edit_member,
            style="Accent.TButton"
        ).pack(pady=10)
        
        # Barra de estado
        status_bar = tk.Frame(self.root, bg=LIGHT_BG, height=25)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_text = tk.StringVar()
        self.status_text.set("Sistema listo")
        
        tk.Label(
            status_bar,
            textvariable=self.status_text,
            bg=LIGHT_BG,
            fg=TEXT_COLOR,
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=10, pady=3)
        
    def register_member(self):
        """Gestiona el registro de un nuevo miembro"""
        # Pedir datos
        dialog = tk.Toplevel(self.root)
        dialog.title("Registrar Miembro")
        dialog.geometry("350x250")
        dialog.configure(bg=DARK_BG)
        dialog.resizable(False, False)
        
        tk.Label(dialog, text="Datos del Miembro", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Formulario
        form = tk.Frame(dialog, bg=DARK_BG)
        form.pack(padx=20, pady=5)
        
        tk.Label(form, text="Nombre:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", pady=5)
        name_var = tk.StringVar()
        tk.Entry(form, textvariable=name_var, width=25).grid(row=0, column=1, pady=5)
        
        tk.Label(form, text="ID Membresía:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", pady=5)
        id_var = tk.StringVar()
        tk.Entry(form, textvariable=id_var, width=25).grid(row=1, column=1, pady=5)
        
        tk.Label(form, text="Fecha Exp.:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=2, column=0, sticky="w", pady=5)
        date_var = tk.StringVar()
        date_var.set(datetime.today().replace(year=datetime.today().year + 1).strftime("%Y-%m-%d"))
        tk.Entry(form, textvariable=date_var, width=25).grid(row=2, column=1, pady=5)
        
        # Botones
        btn_frame = tk.Frame(dialog, bg=DARK_BG)
        btn_frame.pack(pady=15)
        
        result = {"continue": False}
        
        
        
        def on_continue():
            name = name_var.get().strip()
            membership_id = id_var.get().strip()
            exp_date = date_var.get().strip()
            
            if not (name and membership_id and exp_date):
                messagebox.showerror("Error", "Complete todos los campos", parent=dialog)
                return
                
            # Validación de fecha añadida
            try:
                parsed_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                today = datetime.today().date()
                if parsed_date < today:
                    raise ValueError("Fecha expirada")
            except ValueError as e:
                messagebox.showerror("Error", "Fecha expirada o no válida, intenta nuevamente", parent=dialog)
                return

            result["name"] = name
            result["id"] = membership_id
            result["date"] = exp_date
            result["continue"] = True
            dialog.destroy()
            
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Continuar", command=on_continue).pack(side=tk.LEFT, padx=5)
        
        # Esperamos respuesta
        self.root.wait_window(dialog)
        
        # Si canceló, terminar
        if not result["continue"]:
            return
            
        # Capturar rostro
        camera = CameraCapture(self.root)
        roi = camera.start()
        
        if roi is None:
            messagebox.showerror("Error", "No se pudo capturar el rostro")
            return
            
        # Guardar en BD y archivo
        try:
            # Guardar imagen
            img_path = os.path.join(SAMPLES_DIR, f"{result['id']}.png")
            cv.imwrite(img_path, roi)
            
            # Guardar en BD
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                'INSERT INTO members VALUES (?, ?, ?)',
                (result["id"], result["name"], result["date"])
            )
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Éxito", f"Miembro {result['name']} registrado correctamente")
            self.status_text.set(f"Miembro registrado: {result['name']}")
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "El ID de membresía ya existe")
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar: {str(e)}")
    
    def verify_member(self):
        """Verifica el acceso de un miembro"""
        # Entrenar reconocedor
        member_ids = train_recognizer()
        if not member_ids:
            messagebox.showerror("Error", "No hay miembros registrados")
            return
            
        # Capturar rostro
        camera = CameraCapture(self.root)
        roi = camera.start()
        
        if roi is None:
            return
            
        try:
            # Reconocimiento
            label, confidence = recognizer.predict(roi)
            # Verificar umbral de confianza (valores más bajos indican mejor coincidencia en LBPH)
            CONFIDENCE_THRESHOLD = 70  # Ajusta este valor según tus necesidades (50-80 es común)
            if confidence > CONFIDENCE_THRESHOLD:
                messagebox.showwarning("Verificación", 
                                    "No se pudo verificar su identidad con suficiente confianza.\n"
                                    "Por favor, inténtelo de nuevo o contacte al personal.",
                                    parent=self.root)
                return


            membership_id = member_ids[label]
            
            # Buscar en BD
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT name, expiration_date FROM members WHERE membership_id = ?', 
                     (membership_id,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                messagebox.showerror("Error", "Miembro no encontrado en la base de datos")
                return
                
            name, exp_str = row
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            today = datetime.today().date()
            
            # Resultado
            result = tk.Toplevel(self.root)
            result.geometry("400x350")
            result.configure(bg=DARK_BG)
            
            if exp_date >= today:
                # Acceso permitido
                result.title("Acceso Autorizado")
                
                tk.Label(
                    result, 
                    text="✓", 
                    font=("Arial", 48), 
                    bg=DARK_BG, 
                    fg="#4CAF50"
                ).pack(pady=(20, 10))
                
                tk.Label(
                    result, 
                    text=f"Bienvenido, {name}", 
                    font=("Arial", 14, "bold"), 
                    bg=DARK_BG, 
                    fg=TEXT_COLOR
                ).pack(pady=5)
                
                # Info adicional
                info_frame = tk.Frame(result, bg=LIGHT_BG, padx=20, pady=15)
                info_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(
                    info_frame,
                    text=f"ID: {membership_id}\nExp: {exp_date.strftime('%d/%m/%Y')}",
                    bg=LIGHT_BG,
                    fg=TEXT_COLOR,
                    justify=tk.LEFT
                ).pack(anchor="w")
                
                days_left = (exp_date - today).days
                if days_left <= 7:
                    tk.Label(
                        info_frame,
                        text=f"⚠️ Su membresía vence en {days_left} días",
                        bg=LIGHT_BG,
                        fg="#FFC107",
                        font=("Arial", 10, "bold")
                    ).pack(anchor="w", pady=(10, 0))
                
                self.status_text.set(f"Acceso autorizado: {name}")
                self.log_access(name)
                
            else:
                # Acceso denegado
                result.title("Acceso Denegado")
                
                tk.Label(
                    result, 
                    text="✕", 
                    font=("Arial", 48), 
                    bg=DARK_BG, 
                    fg="#F44336"
                ).pack(pady=(20, 10))

                tk.Label(
                    result, 
                    text="Acceso Denegado", 
                    font=("Arial", 14, "bold"), 
                    bg=DARK_BG, 
                    fg=TEXT_COLOR
                ).pack(pady=5)
                
                # Info adicional
                info_frame = tk.Frame(result, bg=LIGHT_BG, padx=20, pady=15)
                info_frame.pack(fill=tk.X, padx=20, pady=10)
                
                tk.Label(
                    info_frame,
                    text=f"Usuario: {name}\nID: {membership_id}",
                    bg=LIGHT_BG,
                    fg=TEXT_COLOR,
                    justify=tk.LEFT
                ).pack(anchor="w")
                
                tk.Label(
                    info_frame,
                    text=f"❌ Membresía vencida ({exp_date.strftime('%d/%m/%Y')})",
                    bg=LIGHT_BG,
                    fg="#F44336",
                    font=("Arial", 10, "bold")
                ).pack(anchor="w", pady=(10, 0))
                
                self.status_text.set(f"Acceso denegado: {name} - Membresía vencida")
            
            # Botón para cerrar
            ttk.Button(
                result,
                text="Aceptar",
                command=result.destroy
            ).pack(pady=15)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error durante la verificación: {str(e)}")
            
    def log_access(self, name):
        """Registra el acceso en el archivo CSV"""
        filename = 'acceso_gimnasio.csv'
        now = datetime.now()
        
        # Verificar si el archivo existe para escribir encabezados
        file_exists = os.path.isfile(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Escribir encabezado si el archivo está vacío o no existe
            if not file_exists or file.tell() == 0:
                writer.writerow(["Fecha", "Hora", "Nombre"])
            
            # Escribir datos del acceso
            writer.writerow([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                name
            ])
    def edit_member(self):
        """Edita los datos de un miembro registrado"""
        # Obtener lista de miembros
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT membership_id, name, expiration_date FROM members')
        members = c.fetchall()
        conn.close()
        
        if not members:
            messagebox.showinfo("Información", "No hay miembros registrados para editar")
            return

        # Crear ventana de edición
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Editar Miembro")
        edit_window.geometry("400x400")
        edit_window.configure(bg=DARK_BG)
        
        # Contenedor principal
        main_frame = tk.Frame(edit_window, bg=DARK_BG)
        main_frame.pack(pady=15, padx=20, fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Editar Miembro", bg=DARK_BG, fg=TEXT_COLOR,font=("Arial", 12, "bold")).pack(pady=10) 
        # Selección de miembro
        tk.Label(main_frame, text="Seleccionar Miembro:", bg=DARK_BG, fg=TEXT_COLOR).pack(anchor="center")
        
        self.selected_member = tk.StringVar()
        member_names = [f"{name} ({id})" for id, name, _ in members]
        member_dropdown = ttk.Combobox(
            main_frame,
            textvariable=self.selected_member,
            values=member_names,
            state="readonly",
            width=30,
            font=("Arial", 10)
        )
        member_dropdown.pack(pady=10, anchor="center")
        
        # Formulario de edición
        form_frame = tk.Frame(main_frame, bg=DARK_BG)
        form_frame.pack(pady=15, anchor="center")
        
        # Campos editables
        tk.Label(form_frame, text="Nombre:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=0, column=0, sticky="e", pady=5)
        self.edit_name = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.edit_name, width=25).grid(row=0, column=1, pady=5, padx=10)
        
        tk.Label(form_frame, text="ID Membresía:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=1, column=0, sticky="e", pady=5)
        self.edit_id = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.edit_id, width=25, state='readonly').grid(row=1, column=1, pady=5, padx=10)
        
        tk.Label(form_frame, text="Fecha Exp.:", bg=DARK_BG, fg=TEXT_COLOR).grid(row=2, column=0, sticky="e", pady=5)
        self.edit_date = tk.StringVar()
        date_entry = tk.Entry(form_frame, textvariable=self.edit_date, width=25)
        date_entry.grid(row=2, column=1, pady=5, padx=10)
       
    
        # Botón para actualizar rostro
        ttk.Button(
            form_frame,
            text="Recapturar Rostro",
            command=lambda: self.update_face(self.edit_id.get()),
            width=20
        ).grid(row=3, column=0, columnspan=2, pady=15, sticky="ew")
        
        # Botones de acción
        button_frame = tk.Frame(main_frame, bg=DARK_BG)
        button_frame.pack(pady=5, anchor="center")
        
        ttk.Button(
            button_frame,
            text="Guardar Cambios",
            command=lambda: self.save_edits(edit_window),
            style="Accent.TButton",
            width=16
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=edit_window.destroy,
            width=8.5
        ).pack(side=tk.LEFT, padx=8)


        # Cargar datos al seleccionar miembro
        def load_member_data(event):
            selected = self.selected_member.get()
            if selected:
                member_id = selected.split("(")[-1].strip(")")
                for m in members:
                    if m[0] == member_id:
                        self.edit_id.set(m[0])
                        self.edit_name.set(m[1])
                        self.edit_date.set(m[2])
                        break

        member_dropdown.bind("<<ComboboxSelected>>", load_member_data)

    def update_face(self, member_id):
        """Actualiza la muestra facial de un miembro"""
        camera = CameraCapture(self.root)
        roi = camera.start()
        
        if roi is not None:
            img_path = os.path.join(SAMPLES_DIR, f"{member_id}.png")
            cv.imwrite(img_path, roi)
            train_recognizer()
            messagebox.showinfo("Éxito", "Muestra facial actualizada correctamente")

    def save_edits(self, window):
        """Guarda los cambios en la base de datos"""
        member_id = self.edit_id.get()
        new_name = self.edit_name.get().strip()
        new_date = self.edit_date.get().strip()

        if not all([member_id, new_name, new_date]):
            messagebox.showerror("Error", "Todos los campos son requeridos")
            return

        try:
            # Validar fecha
            datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE members 
                SET name = ?, expiration_date = ?
                WHERE membership_id = ?
            ''', (new_name, new_date, member_id))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Éxito", "Datos actualizados correctamente")
            window.destroy()
            train_recognizer()  # Reentrenar modelo con posibles nuevas imágenes
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar: {str(e)}")


def main():
    """Función principal"""
    # Inicializar DB y directorios
    init_db()
    
    # Crear interfaz
    root = tk.Tk()
    app = GymAccessApp(root)
    
    # Centrar ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()


if __name__ == '__main__':
    main()