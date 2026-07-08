%% =========================================================================
% 40Gb/s系统色散补偿对比仿真
% 40 Gb/s Dispersion Compensation Comparison
% =========================================================================

clear; clc; close all;

output_dir = '../output/figures';

fprintf('========================================\n');
fprintf('40Gb/s 高速光纤通信系统色散分析\n');
fprintf('40 Gb/s High-Speed Fiber System\n');
fprintf('Dispersion Analysis\n');
fprintf('========================================\n\n');

%% 系统参数
c = 3e8;
lambda = 1550e-9;

% SMF参数
smf_D = 17;         % ps/(nm·km)
smf_alpha = 0.2;    % dB/km
smf_length = 80;    % km
smf_beta2 = -smf_D * lambda^2 / (2*pi*c) * 1e-3;

% DCF参数
dcf_D = -100;        % ps/(nm·km)
dcf_alpha = 0.5;     % dB/km
dcf_length = abs(smf_D * smf_length / dcf_D);

% 调制参数 (40Gb/s)
bitrate_40G = 40e9;
samples_per_bit = 32;
n_bits = 256;
T_bit = 1/bitrate_40G;
dt = T_bit / samples_per_bit;
nt = samples_per_bit * n_bits;
T_window = nt * dt;

dz = 0.05;  % 更小的步长用于40G仿真

fprintf('40G系统参数:\n');
fprintf('  比特率: 40 Gb/s\n');
fprintf('  采样点数: %d\n', nt);
fprintf('  时间步长: %.2f ps\n', dt*1e12);
fprintf('  空间步长: %.2f km\n', dz);

%% 生成测试信号
t = (-nt/2:nt/2-1) * dt;
t_ns = t * 1e9;

rng(42);
bits = randi([0, 1], 1, n_bits);

T_fwhm = T_bit / 2;
T0 = T_fwhm / (2*sqrt(log(2)));
pulse_shape = exp(-t.^2 / (2*T0^2));

power_W = 1e-3;  % 0dBm
signal = zeros(1, nt);
for k = 1:n_bits
    if bits(k) == 1
        center_idx = round((k - 0.5) * samples_per_bit);
        shift = round(center_idx - nt/2);
        signal = signal + bits(k) * circshift(pulse_shape, shift);
    end
end
signal = sqrt(power_W) * signal / max(abs(signal));

fprintf('  信号功率: %.1f dBm\n\n', 10*log10(power_W*1e3));

%% SSFM传输函数
ssfm_40G = @(u, fiber_len, D_coeff, alpha) ssfm_simple(u, fiber_len, D_coeff, alpha, dt, dz, lambda, c);

fprintf('传输仿真中...\n');

% 无补偿传输
signal_no_comp = ssfm_40G(signal, smf_length, smf_D, smf_alpha);
fprintf('  无补偿传输完成 (SMF %.0f km)\n', smf_length);

% DCF补偿传输
signal_with_comp = ssfm_40G(signal_no_comp, dcf_length, dcf_D, dcf_alpha);
fprintf('  DCF补偿完成 (DCF %.2f km)\n', dcf_length);

fprintf('传输仿真完成\n\n');

%% 图7: 40Gb/s时域波形对比
figure('Position', [100, 100, 1200, 800], 'Color', 'w');

subplot(3,1,1);
plot(t_ns, abs(signal).^2 * 1e3, 'b-', 'LineWidth', 1);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title('(a) 40Gb/s发射信号 Transmitted Signal', 'FontSize', 11);
grid on; xlim([-0.3, max(t_ns)+0.3]);

subplot(3,1,2);
plot(t_ns, abs(signal_no_comp).^2 * 1e3, 'r-', 'LineWidth', 1);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title('(b) SMF 80km传输后 (无补偿)', 'FontSize', 11);
grid on; xlim([-0.3, max(t_ns)+0.3]);

subplot(3,1,3);
plot(t_ns, abs(signal_with_comp).^2 * 1e3, 'g-', 'LineWidth', 1);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title('(c) DCF补偿后', 'FontSize', 11);
grid on; xlim([-0.3, max(t_ns)+0.3]);

saveas(gcf, fullfile(output_dir, 'fig7_40G_waveform.png'));
fprintf('图7: 40Gb/s波形对比 已保存\n');

%% 图8: 10G vs 40G 色散受限距离对比
distances = 0:5:200;
q_10G_no_comp = zeros(size(distances));
q_40G_no_comp = zeros(size(distances));
q_10G_comp = zeros(size(distances));
q_40G_comp = zeros(size(distances));

for idx = 1:length(distances)
    L = distances(idx);
    if L == 0
        q_10G_no_comp(idx) = 25;
        q_40G_no_comp(idx) = 25;
        q_10G_comp(idx) = 25;
        q_40G_comp(idx) = 25;
        continue;
    end

    % 色散导致的脉冲展宽因子
    % 对于高斯脉冲，展宽因子 = sqrt(1 + (L/L_D)^2)
    % L_D = T0^2/|beta2| 是色散长度

    % 10G参数
    T0_10G = (50e-12/2) / (2*sqrt(log(2)));
    LD_10G = T0_10G^2 / abs(smf_beta2);

    % 40G参数
    T0_40G = (12.5e-12/2) / (2*sqrt(log(2)));
    LD_40G = T0_40G^2 / abs(smf_beta2);

    broadening_10G = sqrt(1 + (L*1e3/LD_10G)^2);
    broadening_40G = sqrt(1 + (L*1e3/LD_40G)^2);

    q_10G_no_comp(idx) = 25 / broadening_10G;
    q_40G_no_comp(idx) = 25 / broadening_40G;

    % 有补偿 (残余色散5%)
    residual_disp = smf_D * L * 0.05;
    broadening_10G_comp = sqrt(1 + (residual_disp * 0.01)^2);
    broadening_40G_comp = sqrt(1 + (residual_disp * 0.16)^2);
    q_10G_comp(idx) = 25 / broadening_10G_comp;
    q_40G_comp(idx) = 25 / broadening_40G_comp;
end

figure('Position', [100, 100, 900, 600], 'Color', 'w');
plot(distances, q_10G_no_comp, 'b-', 'LineWidth', 1.5); hold on;
plot(distances, q_40G_no_comp, 'r-', 'LineWidth', 1.5);
plot(distances, q_10G_comp, 'b--', 'LineWidth', 1.5);
plot(distances, q_40G_comp, 'r--', 'LineWidth', 1.5);
yline(6, 'k:', 'Q=6 (BER=10^{-9})', 'LineWidth', 1);
xlabel('传输距离 Transmission Distance (km)', 'FontSize', 10);
ylabel('Q因子 Q-Factor (dB)', 'FontSize', 10);
title('10Gb/s与40Gb/s系统色散受限距离对比', 'FontSize', 11);
legend({'10Gb/s 无补偿', '40Gb/s 无补偿', '10Gb/s DCF补偿', '40Gb/s DCF补偿'}, ...
       'Location', 'best', 'FontSize', 9);
grid on;
ylim([0, 28]);

saveas(gcf, fullfile(output_dir, 'fig8_10Gvs40G_distance.png'));
fprintf('图8: 10G vs 40G 距离对比 已保存\n');

%% 图9: 色散补偿方案对比 (预补偿 vs 后补偿 vs 对称补偿)
fprintf('分析不同补偿方案...\n');

% 单脉冲测试
single_pulse = zeros(1, nt);
single_pulse(round(nt/2)) = 1;
single_pulse = single_pulse .* exp(-t.^2/(2*T0^2));
single_pulse = sqrt(power_W) * single_pulse / max(abs(single_pulse));

% 方案1: 后补偿 (SMF -> DCF)
post_comp = ssfm_40G(ssfm_40G(single_pulse, smf_length, smf_D, smf_alpha), ...
                     dcf_length, dcf_D, dcf_alpha);

% 方案2: 预补偿 (DCF -> SMF)
pre_comp = ssfm_40G(ssfm_40G(single_pulse, dcf_length, dcf_D, dcf_alpha), ...
                    smf_length, smf_D, smf_alpha);

% 方案3: 对称补偿 (DCF/2 -> SMF -> DCF/2)
sym_half = ssfm_40G(single_pulse, dcf_length/2, dcf_D, dcf_alpha);
sym_full = ssfm_40G(sym_half, smf_length, smf_D, smf_alpha);
sym_comp = ssfm_40G(sym_full, dcf_length/2, dcf_D, dcf_alpha);

figure('Position', [100, 100, 1200, 500], 'Color', 'w');

subplot(1,3,1);
plot(t_ns, abs(post_comp).^2/max(abs(post_comp).^2), 'b-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 9);
ylabel('归一化功率 Normalized Power', 'FontSize', 9);
title('(a) 后补偿 Post-Compensation', 'FontSize', 10);
grid on; xlim([-0.2, 0.2]); ylim([0, 1.1]);

subplot(1,3,2);
plot(t_ns, abs(pre_comp).^2/max(abs(pre_comp).^2), 'r-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 9);
ylabel('归一化功率 Normalized Power', 'FontSize', 9);
title('(b) 预补偿 Pre-Compensation', 'FontSize', 10);
grid on; xlim([-0.2, 0.2]); ylim([0, 1.1]);

subplot(1,3,3);
plot(t_ns, abs(sym_comp).^2/max(abs(sym_comp).^2), 'g-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 9);
ylabel('归一化功率 Normalized Power', 'FontSize', 9);
title('(c) 对称补偿 Symmetric Compensation', 'FontSize', 10);
grid on; xlim([-0.2, 0.2]); ylim([0, 1.1]);

saveas(gcf, fullfile(output_dir, 'fig9_compensation_schemes.png'));
fprintf('图9: 补偿方案对比 已保存\n');

%% SSFM函数
function u_out = ssfm_simple(u_in, L_km, D_coeff, alpha_dB, dt, dz_km, lambda, c)
    nt = length(u_in);
    L_total = L_km * 1e3;
    dz = dz_km * 1e3;
    nz = max(1, ceil(L_total / dz));
    dz = L_total / nz;

    beta2 = -D_coeff * lambda^2 / (2*pi*c) * 1e-3;
    alpha_lin = alpha_dB / (10*log10(exp(1))) * 1e-3;

    dw = 2*pi / (nt * dt);
    w = (-nt/2:nt/2-1) * dw;
    w = fftshift(w);

    D_half = exp(1i * beta2/2 * w.^2 * dz/2 - alpha_lin * dz/2);
    u = u_in;

    for n = 1:nz
        u_freq = fft(u);
        u_freq = ifftshift(fftshift(u_freq) .* D_half);
        u_time = ifft(u_freq);
        u_freq = fft(u_time);
        u_freq = ifftshift(fftshift(u_freq) .* D_half);
        u = ifft(u_freq);
    end

    u_out = u;
end

fprintf('\n========================================\n');
fprintf('40G对比仿真完成！\n');
fprintf('========================================\n');
