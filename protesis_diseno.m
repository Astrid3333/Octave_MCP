% ============================================================
% PRÓTESIS CLÁSICA TRANSTIBIAL - DISEÑO GEOMÉTRICO EN OCTAVE
% ============================================================
% Genera las coordenadas 3D de una prótesis clásica:
%   1. Pie protésico (perfil lateral - curva Bezier cúbica)
%   2. Tibia/pylon (tubo cilíndrico)
%   3. Socket (conector ovoide)
%   4. Articulación rodilla simplificada
%
% Salida: archivos CSV/JSON con puntos 3D listos para FreeCAD
% ============================================================
clear; clc;
printf('=== PRÓTESIS CLÁSICA TRANSTIBIAL - DISEÑO ===\n\n');

% ---- Parámetros del paciente (estándar adulto) ----
largo_pie_mm      = 260;    % largo total del pie (mm)
ancho_pie_mm      = 100;    % ancho del pie (mm)
alto_pie_mm       = 70;     % alto del pie con tacón (mm)
largo_pylon_mm    = 350;    % largo de la tibia (mm)
diam_pylon_mm     = 30;     % diámetro del pylon (mm)
alto_socket_mm    = 180;    % alto del socketero (mm)
ancho_socket_mm   = 95;     % ancho del socket (mm, eje ant-posterior)
prof_socket_mm    = 85;     % profundidad del socket (mm, eje mediolateral)
angulo_inclin_grados = 7;   % inclinación del pie respecto a la horizontal

printf('Parámetros del paciente:\n');
printf('  Largo pie:     %.0f mm\n', largo_pie_mm);
printf('  Alto pie:      %.0f mm\n', alto_pie_mm);
printf('  Pylon:         %.0f mm (d=%.0f mm)\n', largo_pylon_mm, diam_pylon_mm);
printf('  Socket:        %.0f x %.0f x %.0f mm\n', ancho_socket_mm, prof_socket_mm, alto_socket_mm);
printf('  Inclinación:   %.0f grados\n\n', angulo_inclin_grados);

% ============================================================
% 1. PIE PROTÉSICO - Perfil lateral (curva Bezier cúbica)
% ============================================================
% Puntos de control de la curva Bezier cúbica (vista lateral)
% Simula la forma clásica de un pie SACH (Solid Ankle Cushioned Heel)
printf('[1] Generando perfil del pie protésico...\n');

% Coordenadas de control (mm) - sistema local del pie
% Eje X = ant-posterior, Y = vertical (arriba), Z = 0 (vista lateral)
P0 = [0, 0];           % punta del pie (delante)
P1 = [60, 5];          % zona plantar frontal
P2 = [180, 0];         % talón inferior
P3 = [largo_pie_mm, 0];% talón (atrás)

% Curva Bezier cúbica: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
N_pie = 50;
t = linspace(0, 1, N_pie);
perfil_pie = zeros(N_pie, 2);
for i = 1:N_pie
  tt = t(i);
  perfil_pie(i,:) = (1-tt)^3 * P0 + 3*(1-tt)^2*tt * P1 + 3*(1-tt)*tt^2 * P2 + tt^3 * P3;
endfor

% Parte superior del pie (dorso)
P0d = [0, alto_pie_mm*0.4];    % punta (arriba)
P1d = [80, alto_pie_mm*0.9];   % empeine
P2d = [200, alto_pie_mm*1.0];  % zona alta talón
P3d = [largo_pie_mm, alto_pie_mm*0.7]; % talón (arriba)

perfil_dorso = zeros(N_pie, 2);
for i = 1:N_pie
  tt = t(i);
  perfil_dorso(i,:) = (1-tt)^3 * P0d + 3*(1-tt)^2*tt * P1d + 3*(1-tt)*tt^2 * P2d + tt^3 * P3d;
endfor

% Sección transversal del pie (elipse en el plano XY)
theta = linspace(0, 2*pi, 36);
seccion_pie = zeros(36, 3);
for i = 1:36
  seccion_pie(i,:) = [ancho_pie_mm/2 * cos(theta(i)), alto_pie_mm/2 * sin(theta(i)) + alto_pie_mm/2, 0];
endfor

printf('  Perfil plantar: %d puntos Bezier\n', N_pie);
printf('  Perfil dorsal:  %d puntos Bezier\n', N_pie);
printf('  Sección:        %d puntos elipse\n', 36);

% ============================================================
% 2. PYLON (tibia) - Tubo cilíndrico
% ============================================================
printf('\n[2] Generando pylon (tibia)...\n');

N_circ = 24;            % puntos por circunferencia
N_secc = 10;            % secciones a lo largo del pylon
r_pylon = diam_pylon_mm / 2;
pylon_pts = zeros(N_circ * N_secc, 3);

for j = 1:N_secc
  z = (j-1) / (N_secc-1) * largo_pylon_mm;  % 0 a largo_pylon
  for i = 1:N_circ
    phi = (i-1) / N_circ * 2*pi;
    idx = (j-1)*N_circ + i;
    pylon_pts(idx,:) = [r_pylon*cos(phi), r_pylon*sin(phi), z];
  endfor
endfor

printf('  Tubo: %d circunferencias x %d puntos = %d puntos 3D\n', N_secc, N_circ, N_secc*N_circ);

% ============================================================
% 3. SOCKET (socketero) - Sección ovoide
% ============================================================
printf('\n[3] Generando socket (socketero)...\n');

% Elipse con modificación para forma ovoide (más ancho en mediolateral)
N_puntos_sock = 36;
N_secc_sock = 12;
socket_pts = zeros(N_puntos_sock * N_secc_sock, 3);

for j = 1:N_secc_sock
  z_frac = (j-1) / (N_secc_sock-1);  % 0 (base) a 1 (top)
  z = z_frac * alto_socket_mm;

  % Sección elíptica que cambia con la altura (más estrecho arriba)
  factor = 1 - 0.15 * z_frac;  % se estrecha 15% hacia arriba
  a = ancho_socket_mm / 2 * factor;   % semieje ant-posterior
  b = prof_socket_mm / 2 * factor;    % semieje mediolateral

  for i = 1:N_puntos_sock
    theta_s = (i-1) / N_puntos_sock * 2*pi;
    % Forma ovoide: modificación sutil
    modif = 1 + 0.08 * cos(2*theta_s);
    idx = (j-1)*N_puntos_sock + i;
    socket_pts(idx,:) = [a * modif * cos(theta_s), ...
                         b * modif * sin(theta_s), z];
  endfor
endfor

printf('  Socket: %d secciones x %d puntos = %d puntos 3D\n', N_secc_sock, N_puntos_sock, N_secc_sock*N_puntos_sock);

% ============================================================
% 4. ARTICULACIÓN RODILLA - Eje cilíndrico
% ============================================================
printf('\n[4] Generando articulación de rodilla...\n');

r_rodilla = 15;  % radio del eje de rodilla (mm)
N_circ_r = 20;
largo_eje = 40;  % largo del eje (mm)
eje_pts = zeros(N_circ_r * 4, 3);

% Eje horizontal (a lo largo del eje X)
for j = 1:4
  x = (j-1)/(3) * largo_eje - largo_eje/2;
  for i = 1:N_circ_r
    phi = (i-1)/N_circ_r * 2*pi;
    idx = (j-1)*N_circ_r + i;
    eje_pts(idx,:) = [x, r_rodilla*sin(phi), r_rodilla*cos(phi) + alto_socket_mm];
  endfor
endfor

printf('  Eje rodilla: %d puntos 3D\n', size(eje_pts,1));

% ============================================================
% 5. ENSAMBLAJE - Coordenadas globales
% ============================================================
printf('\n[5] Ensamblando coordenadas globales...\n');

% Sistema de referencia: origen en la base del pie, Z hacia arriba
% El pie va en Z=0 a Z=alto_pie, luego el pylon sube, luego el socket

% Pie: desplazar a origen
pie_completo = [perfil_pie, zeros(N_pie,1); ...        % planta
                perfil_dorso, zeros(N_pie,1)];          % dorso

% Pylon: base en Z = alto_pie, cima en Z = alto_pie + largo_pylon
pylon_global = pylon_pts;
pylon_global(:,3) = pylon_global(:,3) + alto_pie_mm;

% Socket: base en Z = alto_pie + largo_pylon
socket_global = socket_pts;
socket_global(:,3) = socket_global(:,3) + alto_pie_mm + largo_pylon_mm;

% Rodilla: encima del socket
eje_global = eje_pts;
eje_global(:,3) = eje_global(:,3) + alto_pie_mm + largo_pylon_mm;

% Altura total
altura_total = alto_pie_mm + largo_pylon_mm + alto_socket_mm + r_rodilla;
printf('  Altura total: %.0f mm\n', altura_total);

% ============================================================
% 6. EXPORTAR A CSV (para FreeCAD)
% ============================================================
printf('\n[6] Exportando archivos CSV para FreeCAD...\n');

% Pie - planta
fid = fopen('protesis_pie_planta.csv', 'w');
fprintf(fid, 'x,y,z\n');
for i = 1:N_pie
  fprintf(fid, '%.2f,%.2f,%.2f\n', perfil_pie(i,1), perfil_pie(i,2), 0);
endfor
fclose(fid);

% Pie - dorso
fid = fopen('protesis_pie_dorso.csv', 'w');
fprintf(fid, 'x,y,z\n');
for i = 1:N_pie
  fprintf(fid, '%.2f,%.2f,%.2f\n', perfil_dorso(i,1), perfil_dorso(i,2), 0);
endfor
fclose(fid);

% Pylon
fid = fopen('protesis_pylon.csv', 'w');
fprintf(fid, 'x,y,z\n');
for i = 1:size(pylon_global,1)
  fprintf(fid, '%.2f,%.2f,%.2f\n', pylon_global(i,1), pylon_global(i,2), pylon_global(i,3));
endfor
fclose(fid);

% Socket
fid = fopen('protesis_socket.csv', 'w');
fprintf(fid, 'x,y,z\n');
for i = 1:size(socket_global,1)
  fprintf(fid, '%.2f,%.2f,%.2f\n', socket_global(i,1), socket_global(i,2), socket_global(i,3));
endfor
fclose(fid);

% Rodilla
fid = fopen('protesis_rodilla.csv', 'w');
fprintf(fid, 'x,y,z\n');
for i = 1:size(eje_global,1)
  fprintf(fid, '%.2f,%.2f,%.2f\n', eje_global(i,1), eje_global(i,2), eje_global(i,3));
endfor
fclose(fid);

% ============================================================
% 7. EXPORTAR RESUMEN JSON (para FreeCAD)
% ============================================================
printf('[7] Exportando resumen JSON...\n');

fid = fopen('protesis_resumen.json', 'w');
fprintf(fid, '{\n');
fprintf(fid, '  "nombre": "Protesis clasica transtibial",\n');
fprintf(fid, '  "unidades": "mm",\n');
fprintf(fid, '  "componentes": {\n');
fprintf(fid, '    "pie": {"largo": %.0f, "ancho": %.0f, "alto": %.0f},\n', ...
    largo_pie_mm, ancho_pie_mm, alto_pie_mm);
fprintf(fid, '    "pylon": {"largo": %.0f, "diametro": %.0f},\n', ...
    largo_pylon_mm, diam_pylon_mm);
fprintf(fid, '    "socket": {"ancho": %.0f, "profundo": %.0f, "alto": %.0f},\n', ...
    ancho_socket_mm, prof_socket_mm, alto_socket_mm);
fprintf(fid, '    "rodilla": {"radio_eje": %.0f, "largo_eje": %.0f}\n', ...
    r_rodilla, largo_eje);
fprintf(fid, '  },\n');
fprintf(fid, '  "altura_total_mm": %.0f,\n', altura_total);
fprintf(fid, '  "archivos_csv": ["protesis_pie_planta.csv", "protesis_pie_dorso.csv", "protesis_pylon.csv", "protesis_socket.csv", "protesis_rodilla.csv"]\n');
fprintf(fid, '}\n');
fclose(fid);

% ============================================================
% RESUMEN FINAL
% ============================================================
printf('\n=== RESUMEN DEL DISEÑO ===\n');
printf('  Componentes: 4 (pie, pylon, socket, rodilla)\n');
printf('  Altura total: %.0f mm\n', altura_total);
printf('  Archivos CSV: 5\n');
printf('  Resumen JSON: 1\n');
printf('  Puntos totales: %d\n', 2*N_pie + N_secc*N_circ + N_secc_sock*N_puntos_sock + N_circ_r*4);
printf('\n=== DISEÑO COMPLETADO ===\n');
printf('Listo para importar en FreeCAD\n');
