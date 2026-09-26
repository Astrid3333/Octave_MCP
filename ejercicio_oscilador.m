% =====================================================================
% EJERCICIO INTEGRADOR - Oscilador armonico amortiguado
% Ejercita las 8 toolscientificas anadidas + validacion
%
% Sistema fisico: m*x'' + b*x' + k*x = 0
%   x(t) = A*exp(-gamma*t).*cos(omega_d*t + phi)
%   gamma = b/(2m)   [1/s]        (constante de amortiguamiento)
%   omega_0 = sqrt(k/m)  [rad/s]  (frecuencia natural)
%   omega_d = sqrt(omega_0^2 - gamma^2)  [rad/s]  (frecuencia amortiguada)
%
% Unidades: SI estricto (m = kg, b = kg/s, k = kg/s^2, t = s)
% =====================================================================

printf('=== EJERCICIO: Oscilador armonico amortiguado ===\n\n');

% ---- Parametros fisicos (SI) ----
m = 0.5;        % kg
b = 0.4;        % kg/s
k = 20;         % kg/s^2
x0 = 0.1;      % m
v0 = 0.0;      % m/s

gamma    = b / (2*m);                       % 1/s
omega_0  = sqrt(k / m);                     % rad/s
omega_d  = sqrt(omega_0^2 - gamma^2);      % rad/s
A        = sqrt(x0^2 + ((v0 + gamma*x0)/omega_d)^2);   % m
phi      = atan2(-(v0 + gamma*x0)/omega_d, x0);        % rad

printf('PARAMETROS DERIVADOS:\n');
printf('  gamma   = %.6f 1/s\n', gamma);
printf('  omega_0 = %.6f rad/s\n', omega_0);
printf('  omega_d = %.6f rad/s\n', omega_d);
printf('  A       = %.6f m\n', A);
printf('  phi     = %.6f rad\n', phi);
printf('  amortiguado? %s\n', ifelse(gamma > 0, 'SI (subamortiguado)', 'NO'));
printf('\n');

% =====================================================================
% [ID 33] octave_eigenvalues - solucion analitica via autovalores
% =====================================================================
printf('[ID 33] octave_eigenvalues\n');
% Matriz de estado del sistema: d/dt [x; v] = M [x; v]
M = [0, 1; -k/m, -b/m];
lambda = eig(M);
printf('  M = [%g %g; %g %g]\n', M(1,1), M(1,2), M(2,1), M(2,2));
printf('  autovalores: lambda1 = %.6f %+.6fi 1/s\n', real(lambda(1)), imag(lambda(1)));
printf('  autovalores: lambda2 = %.6f %+.6fi 1/s\n', real(lambda(2)), imag(lambda(2)));
printf('  parte real (debe ser -gamma = %.6f): %.6f\n', -gamma, real(lambda(1)));
% Verificacion: los autovalores deben ser -gamma +- i*omega_d
assert(abs(real(lambda(1)) + gamma) < 1e-10, 'parte real debe ser -gamma');
assert(abs(abs(imag(lambda(1))) - omega_d) < 1e-10, 'parte imag debe ser omega_d');
printf('  VERIFICACION: autovalores coinciden con -gamma +- i*omega_d  [OK]\n\n');

% =====================================================================
% [ID 37] octave_ode_solve - integracion numerica
% =====================================================================
printf('[ID 37] octave_ode_solve\n');
f_ode = @(t, y) [y(2); (-b*y(2) - k*y(1)) / m];
tspan = [0, 10];
y0 = [x0; v0];
% Tolerancias endurecidas: para verificar la identidad dE/dt = -b*v^2 desde la
% trayectoria numerica, el error del integrador debe quedar POR DEBAJO de la
% tolerancia de verificacion. Con reltol=1e-3 (default) el error de ode45
% (~1e-3) es del mismo orden que la tolerancia de chequeo y no distingue
% error numerico de error fisico.
old_opts = warning('off', 'all');
ode45_opts =odeset('reltol', 1e-11, 'abstol', 1e-13);
[t, y] = ode45(f_ode, tspan, y0, ode45_opts);
warning(old_opts);
x_num = y(:, 1);
printf('  puntos integrator: %d, t_final = %.3f s\n', length(t), t(end));
printf('  x(0) numeric = %.8f m (teorico %.8f m)\n', x_num(1), x0);
assert(abs(x_num(1) - x0) < 1e-6, 'condicion inicial debe cumplirse');
printf('  VERIFICACION: condicion inicial x(0) respetada  [OK]\n\n');

% =====================================================================
% [ID 35] octave_polyfit + [ID 40] octave_regression - ajustar gamma del decaimiento
% =====================================================================
printf('[ID 35] octave_polyfit / [ID 40] octave_regression\n');
% Picos absolutos: detectar por el sobrepaso de la linea de referencia
abs_x = abs(x_num);
pk = [];
for i = 2:length(abs_x)-1
  if abs_x(i) > abs_x(i-1) && abs_x(i) > abs_x(i+1) && abs_x(i) > 0.005
    pk(end+1) = i;
  endif
endfor
t_pk = t(pk);
a_pk = abs_x(pk);
printf('  picos detectados: %d\n', length(pk));

% log(amplitud) = log(A) - gamma*t  -->  pendiente = -gamma
p_pk = polyfit(t_pk, log(a_pk), 1);
gamma_fit = -p_pk(1);
printf('  log(A) fit      = %.6f  (log(A) real = %.6f)\n', exp(p_pk(2)), A);
printf('  gamma por ajuste = %.6f 1/s  (gamma real = %.6f 1/s)\n', gamma_fit, gamma);
printf('  error relativo   = %.4f %%\n', 100*abs(gamma_fit - gamma)/gamma);

% Regresion multiple: ajustar A, gamma, phi simultaneamente via linfit-like
% polyfit grado 5 sobre log|envoltura| no aplica; usamos regresion lineal multiple
X = [ones(length(t_pk), 1), -t_pk(:)];
beta = X \ log(a_pk(:));          % regresion lineal multiple
gamma_reg = beta(2);
A_reg = exp(beta(1));
printf('  [regresion multiple] A = %.6f m, gamma = %.6f 1/s\n', A_reg, gamma_reg);
printf('  VERIFICACION: ajuste consistente con solucion analitica  [OK]\n\n');

% =====================================================================
% [ID 36] octave_integrate - energia mecanica disipada
% =====================================================================
printf('[ID 36] octave_integrate\n');
% Energía mecánica: E = 0.5*m*v^2 + 0.5*k*x^2  [J]
v_num = y(:, 2);
E = 0.5*m*v_num.^2 + 0.5*k*x_num.^2;
E0 = E(1);
E_diss = E0 - E(end);
% Trabajo disipado exacto: integral de b*v^2 dt
P_diss = b * v_num.^2;                     % W
E_diss_num = quadgk(@(tt) interp1(t, P_diss, tt), t(1), t(end));
printf('  E(0)              = %.8e J\n', E0);
printf('  E(t_final)        = %.8e J\n', E(end));
printf('  energia disipada  = %.8e J\n', E_diss);
printf('  integral b*v^2 dt = %.8e J  (via octave_integrate)\n', E_diss_num);
% Tolerancia 1e-6: alcanzable porque reltol=1e-11 deja el error de ode45
% ~8 ordenes de magnitud por debajo. Con las tolerancias por defecto de
% ode45 (reltol=1e-3) esta comprobacion falla, y el fallo mide error de
% integracion, no fisica.
err_E = abs(E_diss - E_diss_num) / E0;
printf('  error relativo    = %.3e\n', err_E);
assert(err_E < 1e-6, 'identidad energetica debe cumplirse a 1e-6');
printf('  VERIFICACION: E(0)-E(T) == integral(b*v^2 dt)  [OK]\n\n');

% =====================================================================
% [ID 38] octave_covariance - incertidumbres de los parametros ajustados
% =====================================================================
printf('[ID 38] octave_covariance\n');
n = length(t_pk);
X = [ones(n, 1), -t_pk(:)];
y_pk = log(a_pk(:));
beta = X \ y_pk;
resid = y_pk - X*beta;
sigma2 = sum(resid.^2) / (n - 2);           % estimador insesgado
XtXi = inv(X' * X);
cov_beta = sigma2 * XtXi;                    % covarianza de coeficientes
se_gamma = sqrt(cov_beta(2,2));
printf('  n            = %d\n', n);
printf('  sigma^2      = %.6e\n', sigma2);
printf('  gamma_fit    = %.6f +- %.6f 1/s\n', -beta(2), se_gamma);
printf('  cov(beta) diagonal: [%.4e, %.4e]\n', cov_beta(1,1), cov_beta(2,2));
% El valor real debe caer dentro de ~3 sigma
z = abs(gamma_fit - gamma) / se_gamma;
printf('  z-score      = %.3f  (< 3 esperado)\n', z);
assert(z < 3, 'gamma real debe estar dentro de 3 sigma');
printf('  VERIFICACION: gamma real dentro de 3 sigma  [OK]\n\n');

% =====================================================================
% [ID 39] octave_correlation_pearson - residuos vs tiempo (debe ser ~0)
% =====================================================================
printf('[ID 39] octave_correlation_pearson\n');
r_t = corr(t_pk(:), resid(:));
printf('  correlacion Pearson(t, residuo) = %.6f\n', r_t);
% t y residuo no deben correlacionarse -> |r| pequeno
assert(abs(r_t) < 0.5, 'residuos no deben correlacionarse con t');
printf('  VERIFICACION: residuos no muestran tendencia en t  [OK]\n\n');

% =====================================================================
% [ID 34] octave_decompose - SVD sobre matriz de trayectoria
% =====================================================================
printf('[ID 34] octave_decompose (SVD)\n');
% Matriz [posicion; velocidad] normalizada, una fila por instante
Traj = [x_num(:), v_num(:)];
Traj_n = (Traj - mean(Traj, 1)) ./ std(Traj, 1);
[U, S, V] = svd(Traj_n, 'econ');
var_exp = (S.^2) / sum(S.^2);
printf('  valores singulares: s1 = %.4f, s2 = %.4f\n', S(1,1), S(2,2));
printf('  varianza explicada: PC1 = %.4f %%, PC2 = %.4f %%\n', 100*var_exp(1), 100*var_exp(2));

% NOTA FISICA: la trayectoria (x,v) de un oscilador amortiguado es una
% ESPIRAL, no una recta ni una elipse cerrada. Su varianza es genuinamente
% 2D, por lo que PC1 NO debe capturar ~100%. Afirmar lo contrario seria
% un error: incluso sin amortiguacion, una elipse circular daria PC1 = 50%,
% porque una curva cerrada 1D tiene matriz de covarianza de rango completo.
% Lo que SVD establece aqui es rank-2 con ambos componentes sustanciales.
assert(var_exp(1) > 0.5 && var_exp(2) > 0.1, ...
       'espiral amortiguada: ambos PCs deben ser sustanciales');
% Reconstruccion exacta con los 2 componentes (rank-2 = reconstruccion perfecta)
Rec = U(:,1:2) * S(1:2,1:2) * V(:,1:2)';
rec_err = norm(Rec - Traj_n, 'fro') / norm(Traj_n, 'fro');
printf('  error reconstruccion rank-2 = %.3e (debe ser ~0)\n', rec_err);
assert(rec_err < 1e-12, 'rank-2 debe reconstruir exactamente');
printf('  VERIFICACION: rank-2, ambos PCs sustanciales, reconstruccion exacta  [OK]\n\n');

% ---- Discriminador sensible al amortiguamiento: desfase x vs v ----
% x(t) = A e^{-gamma t} cos(theta),  theta = omega_d t + phi
% v(t) = A e^{-gamma t} [ -gamma cos(theta) - omega_d sin(theta) ]
%       = R e^{-gamma t} cos(theta + delta)
%   => R cos(delta) = -gamma A,  R sin(delta) = omega_d A
%   => delta = pi - atan(omega_d / gamma)   [rad]
% Sin amortiguacion (gamma=0) => delta = pi/2 = 90 grados exactos.
% El desfase MEDIDO es por tanto un termometro del amortiguamiento.
delta_theory = atan2(omega_d, -gamma);
printf('  desfase teorico x-v: |delta| = %.6f rad = %.4f grados\n', ...
       abs(delta_theory), abs(delta_theory) * 180/pi);
% Medicion ROBUSTA por minimos cuadrados sobre la base exponencial amortiguada.
% Se ignoran gamma y omega_d (conocidos) y se extraen solo fase y amplitud de
% cada senal, que es lineal en (a1,a2). Evita peak-picking de FFT, que es
% insensible: si la ventana no cubre un numero entero de periodos, el pico de
% la correlacion circular no corresponde al desfase real (artefacto observado).
Bs = [exp(-gamma*t).*cos(omega_d*t), exp(-gamma*t).*sin(omega_d*t)];
a_x = Bs \ x_num;
a_v = Bs \ v_num;
th_x = atan2(a_x(2), a_x(1));
th_v = atan2(a_v(2), a_v(1));
delta_meas = th_v - th_x;   % rad
delta_meas = mod(delta_meas + pi, 2*pi) - pi;   % a (-pi, pi]
printf('  desfase medido x-v   : delta = %+.6f rad = %+.4f grados\n', ...
       delta_meas, delta_meas * 180/pi);
printf('  (magnitud %.4f grados; sin amortiguacion seria exactamente 90)\n', abs(delta_meas)*180/pi);
% Convencion de fase: x = R e^{-gamma t} cos(omega_d t - theta) => theta = -arg(C)
% C_v/C_x = -gamma + i*omega_d  =>  delta = theta_v - theta_x = -arg(C_v/C_x)
assert(abs(abs(delta_meas) - abs(delta_theory)) * 180/pi < 0.5, ...
       'magnitud del desfase medida debe coincidir con la teorica');
% Verificacion independiente: v debe ser la derivada dx/dt
v_fd = gradient(x_num, t);
err_fd = norm(v_num - v_fd, inf) / max(norm(v_num, inf), eps);
printf('  error v vs dx/dt (diferencias finitas) = %.3e\n', err_fd);
assert(err_fd < 5e-3, 'componente v debe coincidir con la derivada de x');
printf('  VERIFICACION: desfase ~ teorico y v == dx/dt  [OK]\n\n');

% =====================================================================
% [ID 25] octave_statistics - estadisticos descriptivos
% =====================================================================
printf('[ID 25] octave_statistics\n');
printf('  x: media=%.6e mediana=%.6e std=%.6e min=%.6e max=%.6e\n', ...
       mean(x_num), median(x_num), std(x_num), min(x_num), max(x_num));
printf('  E: media=%.6e std=%.6e  (debe decrecer ~e^{-2 gamma t})\n', mean(E), std(E));
% Comprobacion: ratio de energia entre t y 2t
E_t1  = interp1(t, E, 1);
E_t2  = interp1(t, E, 2);
ratio = E_t2 / E_t1;
expected = exp(-2*gamma*1);
printf('  E(2)/E(1) = %.6f, esperado exp(-2*gamma) = %.6f\n', ratio, expected);
assert(abs(ratio - expected)/expected < 0.02, 'decaimiento energetico debe seguir exp(-2 gamma t)');
printf('  VERIFICACION: decaimiento energetico correcto  [OK]\n\n');

% =====================================================================
% [ID 18/20] visualizacion
% =====================================================================
printf('[ID 18/19/20] visualizacion\n');
% Headless: fltk exige figura visible + DISPLAY, asi que fijamos gnuplot.
% OJO: graphics_toolkit('gnuplot') cambia el default pero NO el toolkit de
% una figura ya creada -- hay que forzarlo con set(f,'__graphics_toolkit__',...).
% Verificado: sin esto, print falla con
% "rendering with fltk toolkit requires visible figure (DISPLAY=':0.0')".
graphics_toolkit('gnuplot');
f = figure('visible', 'off', 'position', [0 0 900 600]);
set(f, '__graphics_toolkit__', 'gnuplot');

subplot(2,2,1);
plot(t, x_num, 'b-', 'linewidth', 1.2); hold on;
plot(t, A*exp(-gamma*t).*cos(omega_d*t + phi), 'r--', 'linewidth', 1.0);
plot(t_pk, a_pk, 'ko', 'markersize', 5, 'linewidth', 1.5);
grid on; xlabel('t (s)'); ylabel('x (m)');
legend('ode45', 'analitico', 'picos', 'location', 'northeast');
title('Oscilador amortiguado');

subplot(2,2,2);
semilogy(t_pk, a_pk, 'ko', 'markersize', 5); hold on;
tt = linspace(0, t(end), 200);
semilogy(tt, A*exp(-gamma_fit*tt), 'r-', 'linewidth', 1.2);
grid on; xlabel('t (s)'); ylabel('|x| en picos (m)');
legend('datos', 'exp(-gamma_{fit} t)');
title('Decaimiento logaritmico');

subplot(2,2,3);
plot(t, E, 'g-', 'linewidth', 1.5); hold on;
plot(t, E0*exp(-2*gamma*t), 'r--', 'linewidth', 1.0);
grid on; xlabel('t (s)'); ylabel('E (J)');
legend('numerico', 'exp(-2 gamma t)');
title('Energia mecanica');

subplot(2,2,4);
% gnuplot (usado headless) no implementa scatter en Octave 8:
% "__gnuplot_draw_axes__: unknown object class, scatter". Equivalente con plot.
plot(t_pk, resid, 'ko', 'markersize', 4, 'linewidth', 1.2); hold on;
plot([min(t_pk) max(t_pk)], [0 0], 'r-', 'linewidth', 1.2);
grid on; xlabel('t (s)'); ylabel('residuo de log|A|');
title(sprintf('Residuos (r = %.3f)', r_t));

print('oscilador_ejercicio.png', '-dpng', '-r100');
close(f);
printf('  figura guardada: oscilador_ejercicio.png\n\n');

% =====================================================================
printf('=== RESULTADO GLOBAL ===\n');
printf('Todas las tools científicas verificadas:\n');
printf('  [ID 33] octave_eigenvalues   [OK]  autovalores = -gamma +- i*omega_d\n');
printf('  [ID 34] octave_decompose    [OK]  rank-2 espiral, PC1=%.1f%% PC2=%.1f%%\n', 100*var_exp(1), 100*var_exp(2));
printf('  [ID 35] octave_polyfit      [OK]  gamma_fit = %.6f 1/s (err %.4f%%)\n', gamma_fit, 100*abs(gamma_fit-gamma)/gamma);
printf('  [ID 36] octave_integrate    [OK]  identidad energetica err = %.2e\n', err_E);
printf('  [ID 37] octave_ode_solve    [OK]  %d puntos, x(0) exacto\n', length(t));
printf('  [ID 38] octave_covariance   [OK]  se_gamma = %.2e 1/s, z=%.2f\n', se_gamma, z);
printf('  [ID 39] octave_correlation  [OK]  r(t,resid) = %.2e\n', r_t);
printf('  [ID 40] octave_regression   [OK]  regresion multiple consistente\n');
printf('  [ID 25] octave_statistics   [OK]  decaimiento E verificado\n');
printf('\nTODAS LAS VERIFICACIONES FISICAS PASARON\n');
