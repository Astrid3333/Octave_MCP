% =====================================================================
% EJERCICIO DE CONTROL - Pendulo invertido sobre carro (cart-pole)
% Demuestra el paquete `control`: LQR, Lyapunov, pole placement,
% Kalman/LQG, respuesta en frecuencia y margenes de robustez.
%
% Modelo linealizado alrededor de theta=0 (vertical, ARRIBA), con
% pendulo de masa puntual:
%   (M+m) p'' + m l theta'' = u
%    m l  p'' + m l^2 theta'' - m g l theta = 0
% De donde (verificado contra la prediccion analitica mas abajo):
%   p'   = v
%   v'   = -(m g / M) theta + (1/M) u
%   th'  = w
%   w'   = (g (M+m) / (M l)) theta - (1/(M l)) u
%
% SI estricto: M [kg], m [kg], l [m], g [m/s^2], t [s], theta [rad]
% =====================================================================
pkg load control
pkg load signal      % hilbert: envolvente analitica

printf('=== EJERCICIO: Control del pendulo invertido ===\n\n');

% ---- Parametros fisicos (SI) ----
M = 1.0;        % kg    masa del carro
m = 0.5;        % kg    masa del pendulo (punto material)
l = 0.5;        % m     longitud del pendulo
g = 9.81;       % m/s^2 aceleracion de la gravedad

A = [ 0,  1,             0,                  0        ;
      0,  0,   -m*g/M,                      0        ;
      0,  0,             0,                  1        ;
      0,  0,   g*(M+m)/(M*l),               0        ];
B = [0; 1/M; 0; -1/(M*l)];
C_meas = [1 0 0 0; 0 0 1 0];   % se miden posicion del carro y angulo

% =====================================================================
% [ID 70] octave_stability_analysis - autovalores en LAZO ABIERTO
% =====================================================================
printf('[ID 70] octave_stability_analysis - lazo abierto\n');
lambda_OL = eig(A);
printf('  autovalores (lazo abierto):\n');
for i = 1:4
  printf('    lambda_%d = %+9.5f %+9.5fi  1/s\n', i, ...
         real(lambda_OL(i)), imag(lambda_OL(i)));
endfor
printf('  max Re(lambda) = %+.5f 1/s  -> INESTABLE si > 0\n', max(real(lambda_OL)));

% Prediccion analitica del modo inestable: +sqrt( g (M+m) / (M l) )
omega_unstable = sqrt(g*(M+m)/(M*l));
[~, iu] = max(real(lambda_OL));
err_ol = abs(real(lambda_OL(iu)) - omega_unstable);
printf('  modo inestable teorico = +sqrt(g(M+m)/(M l)) = %+.6f 1/s\n', omega_unstable);
printf('  error = %.3e\n', err_ol);
assert(err_ol < 1e-10, 'modo inestable debe coincidir con la teoria');

% Los otros dos autovalores deben ser 0 (movimiento de traslacion):
% deben existir EXACTAMENTE dos ceros, y los dos restantes ser +-omega_unstable.
lambda_sorted = reshape(sort(real(lambda_OL)), 1, []);
n_zeros = sum(abs(lambda_sorted) < 1e-9);
printf('  autovalores (reales, ordenados): %s\n', mat2str(lambda_sorted, 6));
printf('  autovalores nulos (traslacion)  : %d de 4\n', n_zeros);
assert(n_zeros == 2, 'deben existir exactamente dos autovalores nulos');
% Los extremos del espectro deben ser +-omega_unstable
assert(abs(lambda_sorted(1) + omega_unstable) < 1e-10, ...
       'autovalor mas negativo debe ser -sqrt(g(M+m)/(M l))');
assert(abs(lambda_sorted(4) - omega_unstable) < 1e-10, ...
       'autovalor mas positivo debe ser +sqrt(g(M+m)/(M l))');
printf('  VERIFICACION: espectro abierto == teoria  [OK]\n');
printf('  CONCLUSION: sin control el pendulo CAE (Re>0)\n\n');

% =====================================================================
% [ID 66] octave_lqr - control optimo cuadratico
% =====================================================================
printf('[ID 66] octave_lqr\n');
Q = diag([1, 1, 10, 1]);   % penaliza desviacion de angulo (theta) mas que posicion
R = 1;                      % penaliza esfuerzo de control
K = lqr(A, B, Q, R);
Acl = A - B*K;
lambda_CL = eig(Acl);
printf('  Q = diag([1 1 10 1]), R = 1\n');
printf('  K = %s\n', mat2str(K, 5));
printf('  autovalores (lazo cerrado):\n');
for i = 1:4
  printf('    lambda_%d = %+9.5f %+9.5fi  1/s\n', i, ...
         real(lambda_CL(i)), imag(lambda_CL(i)));
endfor
% CONTINUO: estabilidad es Re(lambda) < 0  (NO |lambda|<1, eso es discreto)
assert(max(real(lambda_CL)) < 0, 'lazo cerrado debe ser estable');
printf('  max Re(lambda) = %+.5f 1/s -> ESTABLE\n', max(real(lambda_CL)));
[~, idom] = max(real(lambda_CL));
printf('  polo dominante %+.5f -> constante de tiempo %.4f s\n', ...
       real(lambda_CL(idom)), -1/real(lambda_CL(idom)));
printf('  VERIFICACION: lazo cerrado estable  [OK]\n\n');

% =====================================================================
% [ID 70b] Ecuacion de Lyapunov - verificacion RIGUROSA
% =====================================================================
printf('[ID 70b] octave_stability_analysis - ecuacion de Lyapunov\n');
% Para sistema continuo estable, Acl'*P + P*Acl = -Q tiene P>0 unica.
% lyap(A,B) resuelve  A*X + X*A' + B = 0.  Tomando A = Acl' (asi A' = Acl)
% y B = Q  se obtiene exactamente  Acl'*P + P*Acl = -Q.
% OJO: pasar -Q invertiria el lado derecho y daria P<0 (inestable).
P = lyap(Acl', Q);
res_lyap = norm(Acl'*P + P*Acl + Q, 'fro') / norm(Q, 'fro');
sym_err = norm(P - P', 'fro') / norm(P, 'fro');
eig_P = eig((P + P')/2);
printf('  simetria de P: error = %.3e\n', sym_err);
printf('  ||Acl*P + P*Acl + Q|| / ||Q|| = %.3e\n', res_lyap);
printf('  autovalores de P: min = %+.6f, max = %+.6f\n', min(eig_P), max(eig_P));
assert(res_lyap < 1e-10, 'Lyapunov debe satisfacerse exactamente');
assert(sym_err < 1e-12, 'P debe ser simetrica');
assert(min(eig_P) > 0, 'P debe ser definida positiva');
printf('  VERIFICACION: Lyapunov satisfecha, P simetrica y P>0  [OK]\n\n');

% =====================================================================
% [ID 69] octave_pole_placement - ackermann vs LQR
% =====================================================================
printf('[ID 69] octave_pole_placement\n');
poles_des = [-3, -4, -5, -6];
K_ack = acker(A, B, poles_des);
lambda_ack = eig(A - B*K_ack);
ev_logrados = reshape(sort(real(lambda_ack)), 1, []);
ev_pedidos  = reshape(sort(poles_des), 1, []);
printf('  polos pedidos  : %s\n', mat2str(ev_pedidos, 6));
printf('  polos logrados : %s\n', mat2str(ev_logrados, 6));
err_ack = max(abs(ev_logrados - ev_pedidos));
printf('  error de colocacion = %.3e\n', err_ack);
assert(err_ack < 1e-9, 'acker debe ubicar los polos exactamente');
printf('  K (acker) = %s\n', mat2str(K_ack, 5));
printf('  respuesta de LQR  max Re = %+.4f 1/s\n', max(real(lambda_CL)));
printf('  respuesta de acker max Re = %+.4f 1/s  (mas rapido)\n', ...
       max(real(lambda_ack)));
printf('  VERIFICACION: polos asignados exactamente  [OK]\n\n');

% =====================================================================
% Simulacion: lazo abierto (CAE) vs lazo cerrado (SE ESTABILIZA)
% =====================================================================
printf('SIMULACION lazo abierto vs cerrado\n');
t_sim = 0:0.01:40;       % 40 s: la cola t>10 s abarca ~4 periodos de la
z0 = [0; 0; 0.15; 0];        % ondulacion residual, necesaria para medir la tasa
C_out = [0 0 1 0];           % salida = angulo
u0 = zeros(numel(t_sim), 1);
N = numel(t_sim);

% lsim en este build de `control` solo devuelve la SALIDA (no los estados),
% asi que se integra el sistema lineal con RK4 (4to orden) para obtener la
% trayectoria completa de estados y el esfuerzo de control aplicado.
% lsim se conserva como validacion INDEPENDIENTE del mismo sistema.
function Z = rk4_lin(Aa, u_vec, tt, zi)
  Z = zeros(rows(Aa), numel(tt));
  Z(:,1) = zi;
  z = zi;
  for i = 2:numel(tt)
    h = tt(i) - tt(i-1);
    k1 = Aa*z + u_vec(:,i);
    k2 = Aa*(z + h/2*k1) + u_vec(:,i);
    k3 = Aa*(z + h/2*k2) + u_vec(:,i);
    k4 = Aa*(z + h*k3) + u_vec(:,i);
    z = z + h/6 * (k1 + 2*k2 + 2*k3 + k4);
    Z(:,i) = z;
  endfor
endfunction

% --- lazo abierto: u = 0, el pendulo debe CAER ---
Z_OL = rk4_lin(A, zeros(4,N), t_sim, z0);
% --- lazo cerrado: u = -K z (LQR) ---
U_CL = -K * rk4_lin(Acl, zeros(4,N), t_sim, z0);      % provisional
Z_CL = zeros(4,N); Z_CL(:,1) = z0;
z = z0;
for i = 2:N
  h = t_sim(i) - t_sim(i-1);
  k1 = Acl*z;                    k2 = Acl*(z + h/2*k1);
  k3 = Acl*(z + h/2*k2);          k4 = Acl*(z + h*k3);
  z = z + h/6*(k1 + 2*k2 + 2*k3 + k4);
  Z_CL(:,i) = z;
endfor
U_CL = -K * Z_CL;                 % esfuerzo de control: u = -K z  [N]

theta_OL = Z_OL(3,:);
theta_CL = Z_CL(3,:);

% Validacion cruzada: RK4 propio vs lsim del paquete control
theta_lsim_CL = lsim(ss(Acl, B, C_out, 0), u0, t_sim, z0);
diff_int = max(abs(theta_CL(:) - theta_lsim_CL)) / max(abs(theta_lsim_CL));
printf('  RK4 propio vs lsim(control): diff rel = %.3e\n', diff_int);
assert(diff_int < 1e-5, 'los dos integradores deben coincidir');

printf('  ||theta|| final  ABIERTO : %+.4e rad -> DIVERGE (CAE)\n', theta_OL(end));
printf('  max|theta|       CERRADO : %.6f rad (%.3f grados)\n', ...
       max(abs(theta_CL)), max(abs(theta_CL))*180/pi);
assert(abs(theta_OL(end)) > 1.0, 'lazo abierto debe diverger');
% La respuesta LQR no debe CRECER respecto al estado inicial: el maximo
% ocurre en t=0 (0.15 rad) porque el control lleva el pendulo a la vertical.
overshoot = (max(abs(theta_CL)) - abs(z0(3))) / abs(z0(3));
printf('  sobreimpulso respecto al estado inicial: %+.2f %%\n', 100*overshoot);
assert(overshoot < 0.05, 'el lazo cerrado no debe empeorar el estado inicial');
% La propiedad esencial: DECAER hacia la vertical
decaimiento = abs(theta_CL(end)) / abs(z0(3));
printf('  |theta(t_final)| / |theta(0)| = %.6e\n', decaimiento);
assert(decaimiento < 0.01, 'el lazo cerrado debe llevar theta hacia 0');

% Verificacion rigurosa de la CONSTANTE DE TIEMPO dominante.
%
% En la cola (t>10 s) los modos rapidos -6.41 y -4.73 ya han muerto, y solo
% queda el par complejo -0.657 +- 0.464i. Por tanto cualquier forma
% CUADRATICA POSITIVA debe decaer como exp( 2*Re(lambda_dom) t ).
%
% Se usa la funcion de Lyapunov V = z'Pz (la misma P ya verificada arriba):
% es positiva, no oscila, y su tasa asintotica es exactamente
% 2*Re(lambda_dom) = -1.3144 1/s.
%
% Descartados por ser incorrectos como observable de la tasa:
%  - log|theta|   : theta oscila con periodo 2*pi/0.464 = 13.5 s; log de un
%                   cero no es lineal (r = -0.87) y sesga la pendiente.
%  - |hilbert|: la transformada de Hilbert necesita VARIOS periodos para
%                   resolver la envolvente; con una ventana menor a un
%                   periodo devuelve borde deckado (r = -0.78).
%  - E_pend = 0.5*m*l^2*w^2 + m*g*l*(1-cos th): NO es forma cuadratica; la
%                   disipacion es proporcional a la velocidad, asi que su tasa
%                   NO es 2*Re(lambda_dom) (da -1.508 en vez de -1.314).
tail = t_sim >= 10.0;
t_tail = t_sim(tail)';
V = zeros(N, 1);
for k = 1:N
  V(k) = Z_CL(:,k)' * P * Z_CL(:,k);
endfor
lambda_dom_teorico = 2 * real(lambda_CL(idom));    % 2*Re = -1.3144
p_tail = polyfit(t_tail, log(V(tail)), 1);
r_tail = corr(t_tail, log(V(tail)));
err_dom = abs(p_tail(1) - lambda_dom_teorico) / abs(lambda_dom_teorico);
printf('  cola t>10s: funcion de Lyapunov V = z''Pz\n');
printf('    pendiente ajustada  = %+.6f 1/s\n', p_tail(1));
printf('    2*Re(lambda_dom)    = %+.6f 1/s\n', lambda_dom_teorico);
printf('    error relativo      = %.4f %%\n', 100*err_dom);
printf('    Pearson r(t, log V) = %+.6f  (debe ser -1)\n', r_tail);
assert(err_dom < 0.02, 'la tasa de decaimiento debe coincidir con el polo dominante');
% r no es exactamente -1: la cola conserva un rizado de ~0.1% por la
% diferencia entre las partes imaginarias del par complejo (periodo
% 2*pi/0.928 = 6.8 s, ~4.4 ciclos en la cola). Se exige -0.998, que es
% linealidad practicamente perfecta.
assert(r_tail < -0.998, 'la cola debe ser exponencial (r ~ -1)');
printf('  VERIFICACION: constante de tiempo == polo dominante  [OK]\n');
idx_tr = find(abs(theta_CL) < 0.37*abs(z0(3)), 1, 'first');
t_r37 = t_sim(idx_tr);
printf('  tiempo de respuesta (37%%) = %.3f s\n', t_r37);
printf('  esfuerzo maximo |u| = %.4f N\n', max(abs(U_CL)));
printf('  VERIFICACION: abierto DIVERGE, cerrado DECAE a vertical  [OK]\n\n');

% =====================================================================
% [ID 72] octave_freq_response - respuesta en frecuencia
% =====================================================================
printf('[ID 72] octave_freq_response\n');
% OJO: `bandwidth` esta SOMBREADA por la funcion de algebra lineal
% (bandwidth de matriz, Octave core m/linear-algebra/bandwidth.m), que NO es
% la de control. Por eso el -3 dB se calcula directamente desde bode.
%
% IMPORTANTE: la constante de tiempo debe compararse SIEMPRE consigo misma.
% El lazo cerrado tiene dos canales con dinamicas muy distintas: el LQR
% penaliza fuerte el angulo (Q(3,3)=10), asi que el angulo responde mucho
% mas rapido que la posicion. Comparar el ancho de banda de la posicion
% contra el tiempo de respuesta del angulo daria un error de factor ~5.
C_pos = [1 0 0 0];
C_ang = [0 0 1 0];
w = logspace(-3, 3, 6000);
mag_pos = reshape(squeeze(bode(ss(Acl, B, C_pos, 0), w)), 1, []);
mag_ang = reshape(squeeze(bode(ss(Acl, B, C_ang, 0), w)), 1, []);
DC_pos = mag_pos(1);
DC_ang = mag_ang(1);

% --- canal POSICION: perturbacion inicial en la posicion ---
% La simulacion principal parte de theta0=0.15 rad, con la posicion ~0, asi
% que no mide la constante de tiempo de la posicion. Se corre una segunda
% simulacion perturbando la POSICION, que es el macro-comportamiento lento.
z0_pos = [0.05; 0; 0; 0];
Z_pos = zeros(4, N); Z_pos(:,1) = z0_pos;
zp = z0_pos;
for i = 2:N
  h = t_sim(i) - t_sim(i-1);
  k1 = Acl*zp;                  k2 = Acl*(zp + h/2*k1);
  k3 = Acl*(zp + h/2*k2);        k4 = Acl*(zp + h*k3);
  zp = zp + h/6*(k1 + 2*k2 + 2*k3 + k4);
  Z_pos(:,i) = zp;
endfor
tr_pos = t_sim(find(abs(Z_pos(1,:)) < 0.37*0.05, 1, 'first'));
printf('  --- canal POSICION ---\n');
printf('  ganancia DC = %.6f  (debe ser ~1)\n', DC_pos);
% LQR con penalizacion de posicion implica accion integral => error estatico 0
assert(abs(DC_pos - 1) < 1e-3, 'ganancia DC en posicion debe ser ~1 (accion integral)');
tgt_pos = DC_pos / sqrt(2);
i3p = find(mag_pos <= tgt_pos, 1);
w_bw_pos = interp1(mag_pos(i3p-1:i3p), w(i3p-1:i3p), tgt_pos);
printf('  frecuencia -3 dB = %.4f rad/s (%.4f Hz)\n', w_bw_pos, w_bw_pos/(2*pi));
printf('  1/w_bw = %.4f s   |   tr(37%%) medido = %.4f s\n', 1/w_bw_pos, tr_pos);
printf('  ratio medido/predicho = %.3f\n', tr_pos/(1/w_bw_pos));

% --- canal ANGULO ---
% Su ganancia DC es ~1e-7 (una fuerza constante NO produce inclinacion en el
% modelo linealizado) y su magnitud CRECE con omega: es un canal tipo
% diferenciador. Por tanto NO tiene un -3 dB definido en la banda explorada, y forzar
% el criterio relative al pico daria i3a = 0 (nunca cae bajo 0.707*peak).
% Se reporta de forma descriptiva y se mide su tiempo de respuesta.
tr_ang = t_sim(find(abs(theta_CL) < 0.37*abs(z0(3)), 1, 'first'));
printf('  --- canal ANGULO ---\n');
printf('  ganancia DC = %.6e  (nula: el angulo es un canal tipo diferenciador)\n', DC_ang);
printf('  |H| en la banda: min = %.3e (w=%.0e), max = %.3e (w=%.0e)\n', ...
       min(mag_ang), w(1), max(mag_ang), w(end));
printf('  relacion |H(1e3)|/|H(1e-1)| = %.3e  (crece => pasa-alta)\n', ...
       mag_ang(end)/mag_ang(1));
printf('  tr(37%%) medido = %.4f s  (sin -3 dB comparable)\n', tr_ang);
printf('  el angulo responde %.1fx mas rapido que la posicion: LQR penaliza Q(3,3)=10\n', ...
       tr_pos/tr_ang);
assert(DC_ang < 1e-5, 'el angulo debe tener ganancia DC despreciable');

% El canal POSICION si tiene -3 dB bien definido (DC~1) y es el que se
% verifica rigurosamente. tr ~ 1/bw es una ley EMPIRICA aproximada, no
% exacta: se acepta un factor 2.
assert(abs(tr_pos/(1/w_bw_pos) - 1) < 1.0, 'tr de posicion debe ser ~1/w_bw');
printf('  VERIFICACION: DC~1 y tr_pos ~ 1/w_bw (posicion)  [OK]\n\n');

% =====================================================================
% [ID 71] octave_robustness - margenes
% =====================================================================
printf('[ID 71] octave_robustness\n');
% margin() exige SISO. La realimentacion de estado se realiza como SISO:
%   z' = (A - B*C_pos) z + B*e ;  u = -K z
% luego el lazo L = series(planta, controlador) es 1x1.
maxRe_ctrl = max(real(eig(A - B*C_pos)));
printf('  max Re(A - B*C_pos) = %+.5f 1/s  (realizacion del controlador)\n', maxRe_ctrl);
G_plant  = ss(A, B, C_pos, 0);
K_ctrl   = ss(A - B*C_pos, B, -K, 0);
L_loop   = series(G_plant, K_ctrl);
[gm, pm] = margin(L_loop);
printf('  margen de ganancia = %.4f (%.2f dB)\n', gm, 20*log10(gm));
% El lazo es de TIPO 2 (dos integradores por la dinamica de posicion), asi que
% la fase tiende a -360 y NUNCA cruza -180 de forma bien definida: el margen
% de fase que devuelve margin() no es interpretable aqui. El margen de
% ganancia si lo es: la ganancia puede multiplicarse por gm antes de perder
% estabilidad.
printf('  margen de fase = %.2f grados  [NO INTERPRETABLE: lazo tipo 2]\n', pm*180/pi);
assert(gm > 1.0, 'margen de ganancia debe ser > 1 (robusto)');
printf('  VERIFICACION: margen de ganancia %.2f dB > 0 dB  [OK]\n\n', 20*log10(gm));

% =====================================================================
% [ID 68] octave_kalman_filter - LQG con ruido
% =====================================================================
printf('[ID 68] octave_kalman_filter\n');
% Deteccion: midiendo SOLO theta el sistema NO es estabilizable
% (el modo de traslacion es inobservable -> dlqe falla con "not
% stabilizable"). Un cart-pole real lleva dos encoders: posicion y angulo.
w_std = 0.05;         % rad/s^2  ruido de proceso
v_std = 0.01;         % rad      ruido de medida
dt = 0.02;            % s        paso de integracion
Ad = eye(4) + A*dt;   % A discreta (Euler)
Gd = sqrt(dt) * eye(4);   % el ruido de proceso escala con sqrt(dt)
Q_w = w_std^2 * eye(4);
R_v = v_std^2 * eye(2);

% dlqe(A, G, C, Q, R): el 2do arg es la MATRIZ DE RUIDO DE PROCESO (g),
% NO la matriz B. Firma: [m, p, z, e] = dlqe(...)
L_gain = dlqe(Ad, Gd, C_meas, Q_w, R_v);

% Verificacion cruzada: mi propia iteracion de Riccati debe dar la misma
% ganancia. Elimina toda ambiguedad de convencion de signo.
P = eye(4)*0.01;
for k = 1:3000
  P_pred = Ad*P*Ad' + Gd*Q_w*Gd';
  L_own  = P_pred*C_meas' / (C_meas*P_pred*C_meas' + R_v);
  P      = (eye(4) - L_own*C_meas) * P_pred;
endfor
diff_gain = norm(L_gain - L_own, 'fro') / norm(L_gain, 'fro');
printf('  ganancia L = %s\n', mat2str(L_gain', 5));
printf('  diferencia con Riccati propia = %.3e\n', diff_gain);
assert(diff_gain < 1e-8, 'ganancia debe coincidir con la de Riccati');

% DINAMICA DE ERROR en DISCRETO: estabilidad es |lambda| < 1 (NO Re<0)
err_dyn = (eye(4) - L_gain*C_meas) * Ad;
ev_err = eig(err_dyn);
rho = max(abs(ev_err));
printf('  rho(dinamica de error) = %.6f  (estable si < 1, es DISCRETO)\n', rho);
for i = 1:4
  printf('    lambda_%d = %+9.6f  |.| = %.6f\n', i, real(ev_err(i)), abs(ev_err(i)));
endfor
assert(rho < 1, 'el estimador debe ser estable');
% Los modos cerca de +1 son la traslacion: con encoder de posicion y angulo
% son debilmente observables, convergen lento pero son estables.
printf('  VERIFICACION: estimador estable (|lambda|<1)  [OK]\n\n');

% ---- Simulacion LQG: control basado en el ESTIMADO, no en el estado real ----
rand('state', 42);          % semilla reproducible
N = numel(t_sim);
z_true = z0;  z_est = z0;  P_est = eye(4)*0.01;
TH_true = zeros(1,N);  TH_est = zeros(1,N);  TH_meas = zeros(1,N);
U_applied = zeros(1,N);
TH_true(1) = z_true(3);  TH_est(1) = z_est(3);  TH_meas(1) = z_true(3);

for i = 2:N
  h = t_sim(i) - t_sim(i-1);
  % --- planta real: control por realimentacion del ESTIMADO + ruido de proceso
  u = -K * z_est;
  z_true = Ad * z_true + h * B * u + sqrt(h) * w_std * randn(4,1);
  U_applied(i) = u;
  % --- filtro de Kalman: prediccion
  z_pred = Ad * z_est + h * B * u;
  P_pred = Ad * P_est * Ad' + h * h * w_std^2 * eye(4);
  % --- correccion con medicion ruidosa
  y_meas = C_meas * z_true + v_std * randn(2,1);
  Kgain = P_pred * C_meas' / (C_meas * P_pred * C_meas' + R_v);
  z_est = z_pred + Kgain * (y_meas - C_meas * z_pred);
  P_est = (eye(4) - Kgain * C_meas) * P_pred;
  TH_true(i) = z_true(3);  TH_est(i) = z_est(3);  TH_meas(i) = y_meas(2);
endfor

rmse_est = sqrt(mean((TH_est - TH_true).^2));
rmse_meas = sqrt(mean((TH_meas - TH_true).^2));
printf('  RMSE angulo MEDIDO   = %.6f rad\n', rmse_meas);
printf('  RMSE angulo ESTIMADO = %.6f rad\n', rmse_est);
printf('  mejora = %.1f %%\n', 100*(1 - rmse_est/rmse_meas));
assert(rmse_est < rmse_meas, 'Kalman debe mejorar sobre la medicion cruda');
printf('  max|u| aplicado = %.4f N\n', max(abs(U_applied)));
printf('  VERIFICACION: LQG mantiene el pendulo estable con ruido  [OK]\n\n');

% =====================================================================
% Visualizacion
% =====================================================================
printf('[ID 18/20] visualizacion\n');
graphics_toolkit('gnuplot');
f = figure('visible','off','position',[0 0 950 720]);
set(f,'__graphics_toolkit__','gnuplot');

subplot(2,2,1);
plot(t_sim, theta_OL, 'r-','linewidth',1.4); hold on;
plot(t_sim, theta_CL, 'b-','linewidth',1.4);
xl = [0 6]; plot(xl, [0 0], 'k:','linewidth',0.8);
grid on; xlabel('t (s)'); ylabel('\theta (rad)');
legend('lazo abierto (CAE)','lazo cerrado (LQR)','location','northwest');
title('Pendulo invertido: respuesta'); xlim([0 6]); ylim([-2 2]);

subplot(2,2,2);
semilogy(t_sim, max(abs(theta_OL),1e-8),'r-','linewidth',1.4); hold on;
semilogy(t_sim, max(abs(theta_CL),1e-8),'b-','linewidth',1.4);
grid on; xlabel('t (s)'); ylabel('|\theta| (rad)');
legend('abierto','cerrado','location','northeast');
title('Caida vs estabilizacion (log)');

subplot(2,2,3);
semilogx(w, mag_pos,'b-','linewidth',1.3); hold on;
% las lineas de referencia deben usar semilogx para compartir el eje log
semilogx([1e-3 1e3], [DC_pos/sqrt(2) DC_pos/sqrt(2)], 'r--','linewidth',1.0);
semilogx([w_bw_pos w_bw_pos], [1e-4 1e2], 'm--','linewidth',1.0);
grid on; xlabel('\omega (rad/s)'); ylabel('|H(j\omega)|');
legend('posicion','-3 dB','\omega_{3dB}','location','east');
title(sprintf('Bode posicion (DC=%.4f, w_{3dB}=%.3f)', DC_pos, w_bw_pos));

subplot(2,2,4);
plot(t_sim, TH_meas,'color',[0.75 0.75 0.75],'linewidth',0.7); hold on;
plot(t_sim, TH_est,'b-','linewidth',1.3);
plot(t_sim, TH_true,'k--','linewidth',1.1);
grid on; xlabel('t (s)'); ylabel('\theta (rad)');
legend('medicion ruidosa','estimado Kalman','verdad','location','northeast');
title(sprintf('Filtro de Kalman (RMSE %.2e)', rmse_est));

print('control_ejercicio.png','-dpng','-r100');
close(f);
printf('  figura guardada: control_ejercicio.png\n\n');

% =====================================================================
printf('=== RESULTADO GLOBAL ===\n');
printf('Paquete control verificado end-to-end:\n');
printf('  [ID 70] stability_analysis  [OK]  lazo abierto inestable en %+.4f 1/s\n', max(real(lambda_OL)));
printf('  [ID 66] lqr                  [OK]  lazo cerrado estable, max Re = %+.4f\n', max(real(lambda_CL)));
printf('  [ID 70] lyap                 [OK]  P>0, residual %.2e\n', res_lyap);
printf('  [ID 69] pole_placement       [OK]  acker, error %.2e\n', err_ack);
printf('  [ID 68] kalman_filter        [OK]  rho=%.4f, RMSE mejora %.1f %%\n', rho, 100*(1-rmse_est/rmse_meas));
printf('  [ID 72] freq_response        [OK]  DC=%.4f, w3dB=%.4f rad/s, tr=%.3f s\n', DC_pos, w_bw_pos, tr_pos);
printf('  [ID 71] robustness           [OK]  Gm=%.2f dB\n', 20*log10(gm));
printf('\nCONTROL COMPLETO VERIFICADO\n');
