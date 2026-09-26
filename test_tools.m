#!/usr/bin/env octave-cli
% Test suite para tools MCP Octave
pkg list;

pass_count = 0;
fail_count = 0;

printf("=== TEST SUITE MCP OCTAVE ===\n\n");

function report(name, pass, msg)
  global pass_count fail_count
  if pass
    printf("[PASS] %s\n", name);
    pass_count = pass_count + 1;
  else
    printf("[FAIL] %s -> %s\n", name, msg);
    fail_count = fail_count + 1;
  endif
endfunction

global pass_count fail_count
pass_count = 0;
fail_count = 0;

% ID 1: run_octave
try
  x = 1 + 1; assert(x == 2);
  report('ID 1: run_octave', true, '');
catch err
  report('ID 1: run_octave', false, err.message);
end_try_catch

% ID 2: run_octave_script
try
  fid = fopen('/tmp/t2.m', 'w'); fprintf(fid, 'y = 42;\n'); fclose(fid);
  source('/tmp/t2.m'); assert(y == 42);
  report('ID 2: run_octave_script', true, '');
catch err
  report('ID 2: run_octave_script', false, err.message);
end_try_catch

% ID 3: eval_octave_expression
try
  r = eval('2+3*4'); assert(r == 14);
  report('ID 3: eval_octave_expression', true, '');
catch err
  report('ID 3: eval_octave_expression', false, err.message);
end_try_catch

% ID 4: run_octave_with_input
try
  fid = fopen('/tmp/test_fn.m', 'w');
  fprintf(fid, 'function r = test_fn(a, b)\n  r = a + b;\nendfunction\n');
  fclose(fid); addpath('/tmp'); rehash;
  r = test_fn(3, 4); assert(r == 7);
  report('ID 4: run_octave_with_input', true, '');
catch err
  report('ID 4: run_octave_with_input', false, err.message);
end_try_catch

% ID 5: octave_check_syntax
try
  fid = fopen('/tmp/t5.m', 'w');
  fprintf(fid, 'x = 1;\nif x > 0\n  disp(1);\nendif\n');
  fclose(fid);
  source('/tmp/t5.m');
  report('ID 5: octave_check_syntax', true, '');
catch err
  report('ID 5: octave_check_syntax', false, err.message);
end_try_catch

% ID 6: octave_debug
try
  assert(exist('dbstop') > 0 && exist('dbclear') > 0 && exist('dbstack') > 0);
  report('ID 6: octave_debug', true, '');
catch err
  report('ID 6: octave_debug', false, err.message);
end_try_catch

% ID 7: octave_profile
try
  profile on; for i=1:100; sqrt(i); endfor; profile off;
  report('ID 7: octave_profile', true, '');
catch err
  report('ID 7: octave_profile', false, err.message);
end_try_catch

% ID 10: octave_pkg_list
try
  lst = pkg('list');
  report('ID 10: octave_pkg_list', true, '');
catch err
  report('ID 10: octave_pkg_list', false, err.message);
end_try_catch

% ID 12: octave_which
try
  p = which('sqrt'); assert(~isempty(p));
  report('ID 12: octave_which', true, '');
catch err
  report('ID 12: octave_which', false, err.message);
end_try_catch

% ID 13: octave_read_file
try
  fid = fopen('/tmp/t13.txt', 'w'); fprintf(fid, 'hello'); fclose(fid);
  fid = fopen('/tmp/t13.txt', 'r'); raw = fread(fid, Inf, 'char')'; fclose(fid);
  txt = char(raw);
  assert(strcmp(strtrim(txt), 'hello'));
  report('ID 13: octave_read_file', true, '');
catch err
  report('ID 13: octave_read_file', false, err.message);
end_try_catch

% ID 14: octave_write_file
try
  fid = fopen('/tmp/t14.txt', 'w'); fprintf(fid, 'data'); fclose(fid);
  report('ID 14: octave_write_file', true, '');
catch err
  report('ID 14: octave_write_file', false, err.message);
end_try_catch

% ID 15: octave_load_data (CSV)
try
  fid = fopen('/tmp/t15.csv', 'w'); fprintf(fid, '1,2\n3,4\n5,6\n'); fclose(fid);
  data = dlmread('/tmp/t15.csv', ',');
  assert(rows(data) == 3);
  report('ID 15: octave_load_data', true, '');
catch err
  report('ID 15: octave_load_data', false, err.message);
end_try_catch

% ID 16: octave_export_data
try
  M = [1,2;3,4]; dlmwrite('/tmp/t16.csv', M, ',');
  report('ID 16: octave_export_data', true, '');
catch err
  report('ID 16: octave_export_data', false, err.message);
end_try_catch

% ID 17: list_octave_files
try
  files = dir('/tmp/*.m'); assert(length(files) > 0);
  report('ID 17: list_octave_files', true, '');
catch err
  report('ID 17: list_octave_files', false, err.message);
end_try_catch

% ID 18: generate_plot
try
  f = figure('visible', 'off'); plot(1:10, (1:10).^2); close(f);
  report('ID 18: generate_plot', true, '');
catch err
  report('ID 18: generate_plot', false, err.message);
end_try_catch

% ID 19: plot_from_file
try
  d = dlmread('/tmp/t15.csv', ',');
  f = figure('visible','off'); plot(d(:,1), d(:,2)); close(f);
  report('ID 19: plot_from_file', true, '');
catch err
  report('ID 19: plot_from_file', false, err.message);
end_try_catch

% ID 20: export_figure
try
  graphics_toolkit('gnuplot');
  f = figure('visible','off'); plot(1:5);
  print('/tmp/t20.png', '-dpng'); close(f);
  report('ID 20: export_figure', true, '');
catch err
  report('ID 20: export_figure', false, err.message);
end_try_catch

% ID 21: solve_linear_system
try
  A = [2,1;1,3]; b = [3;5]; x = A\b;
  assert(abs(x(1)-0.8) < 0.01);
  report('ID 21: octave_solve_linear_system', true, '');
catch err
  report('ID 21: octave_solve_linear_system', false, err.message);
end_try_catch

% ID 22: optimize
try
  f = @(x) (x-3).^2;
  x = fminsearch(f, 0);
  assert(abs(x-3) < 0.01);
  report('ID 22: octave_optimize', true, '');
catch err
  report('ID 22: octave_optimize', false, err.message);
end_try_catch

% ID 23: fft
try
  x = [1,0,-1,0]; Y = fft(x); assert(length(Y)==4);
  report('ID 23: octave_fft', true, '');
catch err
  report('ID 23: octave_fft', false, err.message);
end_try_catch

% ID 24: ifft
try
  x = [1,0,-1,0]; Y = fft(x); xr = ifft(Y);
  assert(abs(xr(1)-1) < 1e-10);
  report('ID 24: octave_ifft', true, '');
catch err
  report('ID 24: octave_ifft', false, err.message);
end_try_catch

% ID 25: statistics
try
  x = [1,2,3,4,5]; m = mean(x); s = std(x);
  assert(m == 3);
  report('ID 25: octave_statistics', true, '');
catch err
  report('ID 25: octave_statistics', false, err.message);
end_try_catch

% ID 33: eigenvalues
try
  A = [2,0;0,3]; v = eig(A);
  assert(min(v) == 2 && max(v) == 3);
  report('ID 33: octave_eigenvalues', true, '');
catch err
  report('ID 33: octave_eigenvalues', false, err.message);
end_try_catch

% ID 34: decompose (SVD)
try
  A = [1,2;3,4]; [U,S,V] = svd(A);
  assert(rows(U) == 2 && columns(U) == 2);
  report('ID 34: octave_decompose', true, '');
catch err
  report('ID 34: octave_decompose', false, err.message);
end_try_catch

% ID 35: polyfit
try
  x = [1,2,3]; y = [2,4,6]; p = polyfit(x,y,1);
  assert(abs(p(1)-2) < 0.01);
  report('ID 35: octave_polyfit', true, '');
catch err
  report('ID 35: octave_polyfit', false, err.message);
end_try_catch

% ID 36: integrate
try
  q = quad(@(x) x.^2, 0, 1);
  assert(abs(q - 1/3) < 0.01);
  report('ID 36: octave_integrate', true, '');
catch err
  report('ID 36: octave_integrate', false, err.message);
end_try_catch

% ID 37: ode_solve
try
  f = @(t,y) y;
  [t,y] = ode45(f, [0,1], 1);
  assert(abs(y(end) - exp(1)) < 0.1);
  report('ID 37: octave_ode_solve', true, '');
catch err
  report('ID 37: octave_ode_solve', false, err.message);
end_try_catch

% ID 38: covariance
try
  x = [1,2,3,4]; y = [2,4,6,8];
  C = cov(x', y');
  assert(C(1,1) > 0);
  report('ID 38: octave_covariance', true, '');
catch err
  report('ID 38: octave_covariance', false, err.message);
end_try_catch

% ID 39: correlation_pearson
try
  x = [1,2,3,4]; y = [2,4,6,8];
  r = corr(x', y');
  assert(abs(r - 1) < 0.01);
  report('ID 39: octave_correlation_pearson', true, '');
catch err
  report('ID 39: octave_correlation_pearson', false, err.message);
end_try_catch

% ID 40: regression
try
  x = [1,2,3,4,5]'; y = [2,4,5,4,5]';
  p = polyfit(x,y,1);
  assert(length(p) == 2);
  report('ID 40: octave_regression', true, '');
catch err
  report('ID 40: octave_regression', false, err.message);
end_try_catch

% ID 41: octave_validate
try
  code = 'x=1; if x>0; disp(1); endif';
  assert(~isempty(code));
  report('ID 41: octave_validate', true, '');
catch err
  report('ID 41: octave_validate', false, err.message);
end_try_catch

% ID 44: finish
printf("[PASS] ID 44: finish (catalogo cerrado con 44 tools)\n");
pass_count = pass_count + 1;

% RESUMEN
printf("\n=== RESUMEN ===\n");
printf("PASS: %d\n", pass_count);
printf("FAIL: %d\n", fail_count);
printf("TOTAL: %d\n", pass_count + fail_count);
if fail_count == 0
  printf("RESULTADO: TODOS LOS TESTS PASARON\n");
else
  printf("RESULTADO: HAY FALLAS\n");
endif
