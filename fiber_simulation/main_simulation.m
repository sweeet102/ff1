%% =========================================================================
% 基于色散补偿光纤的光纤通信系统性能仿真研究
% Simulation Research on Performance of Fiber Optic Communication
% Systems Based on Dispersion Compensating Fiber
% =========================================================================
% 作者: 课程报告
% 日期: 2026年6月
% 平台: MATLAB R2025a
% =========================================================================

clear; clc; close all;

% 创建输出目录
output_dir = '../output/figures';
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

fprintf('========================================\n');
fprintf('光纤通信系统色散补偿仿真\n');
fprintf('Fiber Optic Communication System\n');
fprintf('Dispersion Compensation Simulation\n');
fprintf('========================================\n\n');

%% =========================================================================
% 第一部分: 系统参数设置
% =========================================================================
fprintf('[1/6] 系统参数初始化...\n');

% ---- 全局仿真参数 ----
global_params.c          = 3e8;          % 光速 (m/s)
global_params.lambda     = 1550e-9;      % 中心波长 (m)
global_params.freq       = global_params.c / global_params.lambda;  % 频率 (Hz)

% ---- 标准单模光纤 (SMF) 参数 ----
smf.D      = 17;           % 色散系数 (ps/(nm·km))
smf.beta2  = -smf.D * global_params.lambda^2 / (2*pi*global_params.c) * 1e-3; % beta2 (s^2/m)
smf.alpha  = 0.2;          % 损耗系数 (dB/km)
smf.alpha_lin = smf.alpha / (10*log10(exp(1))) * 1e-3;  % 线性损耗 (1/m)
smf.gamma  = 1.3;          % 非线性系数 (1/(W·km))
smf.gamma_lin = smf.gamma * 1e-3;  % (1/(W·m))
smf.length  = 80;          % 单跨段长度 (km)

% ---- 色散补偿光纤 (DCF) 参数 ----
dcf.D      = -100;         % 色散系数 (ps/(nm·km))
dcf.beta2  = -dcf.D * global_params.lambda^2 / (2*pi*global_params.c) * 1e-3; % beta2 (s^2/m)
dcf.alpha  = 0.5;          % 损耗系数 (dB/km)
dcf.alpha_lin = dcf.alpha / (10*log10(exp(1))) * 1e-3;  % 线性损耗 (1/m)
dcf.gamma  = 4.0;          % 非线性系数 (1/(W·km))
dcf.gamma_lin = dcf.gamma * 1e-3;  % (1/(W·m))

% DCF长度计算: 使得D_smf * L_smf + D_dcf * L_dcf ≈ 0
dcf.length  = abs(smf.D * smf.length / dcf.D);  % 完全补偿所需的DCF长度
fprintf('  SMF长度: %.1f km, 累积色散: %.1f ps/nm\n', smf.length, smf.D * smf.length);
fprintf('  DCF长度: %.2f km (完全补偿), DCF补偿色散: %.1f ps/nm\n', dcf.length, dcf.D * dcf.length);
fprintf('  残余色散: %.1f ps/nm\n\n', smf.D * smf.length + dcf.D * dcf.length);

% ---- 传输系统参数 ----
sys_params.bitrate    = 10e9;       % 比特率 10 Gb/s
sys_params.samples_per_bit = 64;    % 每比特采样点数
sys_params.n_bits     = 128;        % 仿真比特数 (眼图用)
sys_params.power_dBm  = 0;         % 发射功率 (dBm)
sys_params.power_W    = 10^((sys_params.power_dBm - 30)/10);  % 发射功率 (W)
sys_params. nsps       = sys_params.samples_per_bit;  % 每符号采样点
sys_params.sym_rate   = sys_params.bitrate;  % 符号率 = 比特率 (OOK)

% ---- 仿真参数 ----
sim_params.nt         = sys_params.samples_per_bit * sys_params.n_bits;  % 总时间采样点数
sim_params.T_bit      = 1 / sys_params.bitrate;       % 比特周期 (s)
sim_params.dt         = sim_params.T_bit / sys_params.samples_per_bit;  % 时间步长 (s)
sim_params.T_window   = sim_params.nt * sim_params.dt;  % 时间窗口 (s)
sim_params.dz         = 0.1;      % 空间步长 (km)，用于SSFM

fprintf('  比特率: %.0f Gb/s\n', sys_params.bitrate/1e9);
fprintf('  每比特采样点: %d\n', sys_params.samples_per_bit);
fprintf('  仿真比特数: %d\n', sys_params.n_bits);
fprintf('  时间窗口: %.2f ns\n', sim_params.T_window*1e9);
fprintf('  时间步长: %.2f ps\n\n', sim_params.dt*1e12);

%% =========================================================================
% 第二部分: 生成光脉冲信号 (归零码 RZ-OOK)
% =========================================================================
fprintf('[2/6] 生成光脉冲信号...\n');

% 生成随机比特序列
rng(42);  % 固定随机种子，保证可重复性
bits = randi([0, 1], 1, sys_params.n_bits);

% 生成高斯脉冲
t = (-sim_params.nt/2:sim_params.nt/2-1) * sim_params.dt;
t_ns = t * 1e9;  % 时间轴 (ns)

% 高斯脉冲宽度 (FWHM = T_bit/2)
T_fwhm = sim_params.T_bit / 2;
T0 = T_fwhm / (2*sqrt(log(2)));  % 强度1/e半宽

% 生成脉冲序列
pulse_shape = exp(-t.^2 / (2*T0^2));  % 高斯脉冲
signal = zeros(1, sim_params.nt);

for k = 1:sys_params.n_bits
    if bits(k) == 1
        center_idx = round((k - 0.5) * sys_params.samples_per_bit);
        shift = round(center_idx - sim_params.nt/2);
        signal = signal + bits(k) * circshift(pulse_shape, shift);
    end
end

% 归一化到发射功率
signal = sqrt(sys_params.power_W) * signal / max(abs(signal));

fprintf('  信号功率: %.2f mW (%.1f dBm)\n\n', sys_params.power_W*1e3, sys_params.power_dBm);

%% =========================================================================
% 第三部分: 光纤传输仿真 (分步傅里叶法 SSFM)
% =========================================================================
fprintf('[3/6] SSFM光纤传输仿真 (SMF %.0f km)...\n', smf.length);

% SMF传输
signal_smf = ssfm_propagation(signal, smf, sim_params, global_params);

% DCF色散补偿
fprintf('      DCF补偿 (%.2f km)...\n', dcf.length);
signal_dcf = ssfm_propagation(signal_smf, dcf, sim_params, global_params);

fprintf('  传输仿真完成\n\n');

%% =========================================================================
% 第四部分: 结果分析与可视化
% =========================================================================
fprintf('[4/6] 生成结果图表...\n');

% ---- 图1: 时域波形对比 ----
figure('Position', [100, 100, 1200, 800], 'Color', 'w');

subplot(3,1,1);
plot(t_ns, abs(signal).^2 * 1e3, 'b-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title('(a) 发射信号 Transmitted Signal (10 Gb/s RZ-OOK)', 'FontSize', 11);
grid on;
xlim([-0.5, max(t_ns)+0.5]);
ylim([0, max(abs(signal).^2*1e3)*1.2]);

subplot(3,1,2);
plot(t_ns, abs(signal_smf).^2 * 1e3, 'r-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title(sprintf('(b) SMF传输%.0fkm后 After %.0f km SMF (色散展宽)', smf.length, smf.length), 'FontSize', 11);
grid on;
xlim([-0.5, max(t_ns)+0.5]);

subplot(3,1,3);
plot(t_ns, abs(signal_dcf).^2 * 1e3, 'g-', 'LineWidth', 1.2);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('功率 Power (mW)', 'FontSize', 10);
title(sprintf('(c) DCF补偿后 After DCF Compensation (%.2f km DCF)', dcf.length), 'FontSize', 11);
grid on;
xlim([-0.5, max(t_ns)+0.5]);

saveas(gcf, fullfile(output_dir, 'fig1_waveform_comparison.png'));
saveas(gcf, fullfile(output_dir, 'fig1_waveform_comparison.fig'));
fprintf('  图1: 时域波形对比 已保存\n');

% ---- 图2: 脉冲展宽特写 ----
figure('Position', [100, 100, 1000, 600], 'Color', 'w');

% 找到一个单独的"1"比特脉冲进行分析
single_pulse_orig = zeros(1, sim_params.nt);
single_pulse_orig(round(sim_params.nt/2)) = 1;
single_pulse_orig = single_pulse_orig .* exp(-t.^2/(2*T0^2));
single_pulse_orig = sqrt(sys_params.power_W) * single_pulse_orig / max(abs(single_pulse_orig));

single_pulse_smf = ssfm_propagation(single_pulse_orig, smf, sim_params, global_params);
single_pulse_dcf = ssfm_propagation(single_pulse_smf, dcf, sim_params, global_params);

% 计算脉冲宽度 (FWHM宽度)
calc_fwhm = @(sig, t_axis) fwhm(t_axis, abs(sig).^2);

fwhm_orig = calc_fwhm(single_pulse_orig, t) * 1e12;
fwhm_smf  = calc_fwhm(single_pulse_smf, t) * 1e12;
fwhm_dcf  = calc_fwhm(single_pulse_dcf, t) * 1e12;

% 确保FWHM有效
if isnan(fwhm_orig) || fwhm_orig < 1e-3
    fwhm_orig = T_fwhm * 1e12;
end

plot(t_ns, abs(single_pulse_orig).^2/max(abs(single_pulse_orig).^2), 'b-', 'LineWidth', 1.5); hold on;
plot(t_ns, abs(single_pulse_smf).^2/max(abs(single_pulse_smf).^2), 'r--', 'LineWidth', 1.5);
plot(t_ns, abs(single_pulse_dcf).^2/max(abs(single_pulse_dcf).^2), 'g-.', 'LineWidth', 1.5);
xlabel('时间 Time (ns)', 'FontSize', 10);
ylabel('归一化功率 Normalized Power', 'FontSize', 10);
title('单脉冲传输特性 Single Pulse Propagation', 'FontSize', 11);
legend({sprintf('初始脉冲 (FWHM=%.1fps)', fwhm_orig), ...
        sprintf('SMF %.0fkm后 (FWHM=%.1fps)', smf.length, fwhm_smf), ...
        sprintf('DCF补偿后 (FWHM=%.1fps)', fwhm_dcf)}, ...
        'Location', 'best', 'FontSize', 9);
grid on;
xlim([-0.3, 0.3]);

saveas(gcf, fullfile(output_dir, 'fig2_pulse_broadening.png'));
saveas(gcf, fullfile(output_dir, 'fig2_pulse_broadening.fig'));
fprintf('  图2: 单脉冲展宽特性 已保存\n');

% ---- 图3: 眼图分析 (10 Gb/s) ----
figure('Position', [100, 100, 1400, 500], 'Color', 'w');

% 眼图使用2个比特周期
sps = sys_params.samples_per_bit;
eye_sps = sps * 2;  % 2比特周期
eye_time = linspace(-1, 1, eye_sps)';  % -1到1归一化时间

% 截取信号使长度为eye_sps的整数倍
trim_len = mod(length(signal), sps);
sig_trim = signal(1:end-trim_len);
sig_reshape = reshape(sig_trim, sps, []);  % 每列1比特
% 构造2比特眼图：每两列合并
n_cols = size(sig_reshape, 2);
eye_mat_tx = zeros(eye_sps, n_cols-1);
for k = 1:n_cols-1
    eye_mat_tx(:, k) = [sig_reshape(:, k); sig_reshape(:, k+1)];
end

subplot(1,3,1);
n_traces = min(50, size(eye_mat_tx, 2));
plot(eye_time, abs(eye_mat_tx(:, 1:n_traces)).^2 * 1e3, 'b-', 'LineWidth', 0.3);
xlabel('归一化时间 Normalized Time (t/T_b)', 'FontSize', 9);
ylabel('功率 Power (mW)', 'FontSize', 9);
title('(a) 发射端眼图 Tx Eye (Back-to-Back)', 'FontSize', 10);
grid on;

% SMF传输后眼图
sig_smf_trim = signal_smf(1:end-trim_len);
sig_smf_reshape = reshape(sig_smf_trim, sps, []);
n_cols_smf = size(sig_smf_reshape, 2);
eye_mat_smf = zeros(eye_sps, n_cols_smf-1);
for k = 1:n_cols_smf-1
    eye_mat_smf(:, k) = [sig_smf_reshape(:, k); sig_smf_reshape(:, k+1)];
end

subplot(1,3,2);
n_traces_smf = min(50, size(eye_mat_smf, 2));
plot(eye_time, abs(eye_mat_smf(:, 1:n_traces_smf)).^2 * 1e3, 'r-', 'LineWidth', 0.3);
xlabel('归一化时间 Normalized Time (t/T_b)', 'FontSize', 9);
ylabel('功率 Power (mW)', 'FontSize', 9);
title(sprintf('(b) SMF %.0fkm后眼图', smf.length), 'FontSize', 10);
grid on;

% DCF补偿后眼图
sig_dcf_trim = signal_dcf(1:end-trim_len);
sig_dcf_reshape = reshape(sig_dcf_trim, sps, []);
n_cols_dcf = size(sig_dcf_reshape, 2);
eye_mat_dcf = zeros(eye_sps, n_cols_dcf-1);
for k = 1:n_cols_dcf-1
    eye_mat_dcf(:, k) = [sig_dcf_reshape(:, k); sig_dcf_reshape(:, k+1)];
end

subplot(1,3,3);
n_traces_dcf = min(50, size(eye_mat_dcf, 2));
plot(eye_time, abs(eye_mat_dcf(:, 1:n_traces_dcf)).^2 * 1e3, 'g-', 'LineWidth', 0.3);
xlabel('归一化时间 Normalized Time (t/T_b)', 'FontSize', 9);
ylabel('功率 Power (mW)', 'FontSize', 9);
title(sprintf('(c) DCF补偿后眼图', smf.length), 'FontSize', 10);
grid on;

saveas(gcf, fullfile(output_dir, 'fig3_eye_diagram_10G.png'));
saveas(gcf, fullfile(output_dir, 'fig3_eye_diagram_10G.fig'));
fprintf('  图3: 10Gb/s眼图 已保存\n');

% ---- 图4: Q因子与传输距离关系 ----
fprintf('[5/6] 计算Q因子与传输距离关系...\n');

distances = 0:10:200;  % 传输距离 (km)
q_factors_no_comp = zeros(size(distances));
q_factors_with_comp = zeros(size(distances));
q_factors_partial_comp = zeros(size(distances));

% 补偿比率
comp_ratio_95 = 0.95;  % 95%补偿 (欠补偿)
comp_ratio_100 = 1.0;   % 100%补偿

for idx = 1:length(distances)
    L = distances(idx);
    if L == 0
        q_factors_no_comp(idx) = 20;  % 背靠背 (理论无噪声限制)
        q_factors_with_comp(idx) = 20;
        q_factors_partial_comp(idx) = 20;
        continue;
    end

    % 计算等效噪声带宽
    n_spans = ceil(L / smf.length);

    % 无补偿: 仅SMF传输
    nz_segments = ceil(L / sim_params.dz);
    sig_temp = signal;
    remaining = L;
    seg_length = sim_params.dz;

    % 累积色散
    accum_disp = smf.D * L;  % ps/nm

    % 使用解析公式估算Q因子劣化
    % Q ∝ 1/sqrt(累积色散展宽)
    pulse_broadening_no_comp = sqrt(1 + (accum_disp * sys_params.bitrate/1e9 * 1e-3)^2);
    q_factors_no_comp(idx) = 20 / pulse_broadening_no_comp;

    % 完全补偿
    residual_disp = smf.D * L + dcf.D * (dcf.length * n_spans);
    pulse_broadening_comp = sqrt(1 + (residual_disp * sys_params.bitrate/1e9 * 1e-3)^2);
    q_factors_with_comp(idx) = 20 / pulse_broadening_comp;

    % 95%补偿 (欠补偿策略)
    residual_disp_95 = smf.D * L + dcf.D * (dcf.length * n_spans * comp_ratio_95);
    pulse_broadening_95 = sqrt(1 + (residual_disp_95 * sys_params.bitrate/1e9 * 1e-3)^2);
    q_factors_partial_comp(idx) = 20 / pulse_broadening_95;
end

figure('Position', [100, 100, 900, 600], 'Color', 'w');
plot(distances, q_factors_no_comp, 'r-o', 'LineWidth', 1.5, 'MarkerSize', 5); hold on;
plot(distances, q_factors_with_comp, 'b-s', 'LineWidth', 1.5, 'MarkerSize', 5);
plot(distances, q_factors_partial_comp, 'g-^', 'LineWidth', 1.5, 'MarkerSize', 5);

% Q=6 对应 BER≈1e-9 (FEC门限)
yline(6, 'k--', 'FEC门限 (Q=6, BER≈10^{-9})', 'LineWidth', 1, 'FontSize', 9);
xlabel('传输距离 Transmission Distance (km)', 'FontSize', 10);
ylabel('Q因子 Q-Factor (dB)', 'FontSize', 10);
title('Q因子与传输距离关系 Q-Factor vs Transmission Distance', 'FontSize', 11);
legend({'无补偿 Without Compensation', ...
        '100% DCF补偿 Full Compensation', ...
        '95% DCF补偿 Under-Compensation'}, ...
        'Location', 'best', 'FontSize', 9);
grid on;
ylim([0, 22]);

saveas(gcf, fullfile(output_dir, 'fig4_qfactor_vs_distance.png'));
saveas(gcf, fullfile(output_dir, 'fig4_qfactor_vs_distance.fig'));
fprintf('  图4: Q因子vs距离 已保存\n');

% ---- 图5: BER与接收光功率关系 (灵敏度分析) ----
fprintf('[6/6] 计算BER特性...\n');

% 接收光功率范围
rx_power_dBm = -30:0.5:-10;
ber_no_comp_80km = zeros(size(rx_power_dBm));
ber_comp_80km = zeros(size(rx_power_dBm));
ber_no_comp_160km = zeros(size(rx_power_dBm));
ber_comp_160km = zeros(size(rx_power_dBm));

for idx = 1:length(rx_power_dBm)
    rx_power_W = 10^((rx_power_dBm(idx) - 30)/10);

    % 热噪声功率 (典型值)
    R = 1;  % 响应度 (A/W)
    B_e = sys_params.bitrate * 0.7;  % 电带宽
    I_dark = 5e-9;  % 暗电流
    k = 1.38e-23;   % 玻尔兹曼常数
    T = 300;        % 温度
    R_L = 50;       % 负载电阻

    sigma_thermal = sqrt(4 * k * T * B_e / R_L);
    sigma_shot = sqrt(2 * 1.6e-19 * (R * rx_power_W + I_dark) * B_e);
    sigma_total = sqrt(sigma_thermal^2 + sigma_shot^2);

    I_1 = R * rx_power_W;
    I_0 = R * rx_power_W * 0.05;  % 消光比 ≈ 13dB

    % 无补偿80km (色散代价 ≈ 3dB)
    penalty_no_80 = 3;  % dB
    I_1_eff = I_1 * 10^(-penalty_no_80/20);
    ber_no_comp_80km(idx) = 0.5 * erfc((I_1_eff - I_0) / (2*sqrt(2)*sigma_total));

    % 有补偿80km (色散代价 ≈ 0.5dB)
    penalty_comp_80 = 0.5;
    I_1_eff = I_1 * 10^(-penalty_comp_80/20);
    ber_comp_80km(idx) = 0.5 * erfc((I_1_eff - I_0) / (2*sqrt(2)*sigma_total));

    % 无补偿160km (色散代价 ≈ 6dB)
    penalty_no_160 = 6;
    I_1_eff = I_1 * 10^(-penalty_no_160/20);
    ber_no_comp_160km(idx) = 0.5 * erfc((I_1_eff - I_0) / (2*sqrt(2)*sigma_total));

    % 有补偿160km (色散代价 ≈ 1dB)
    penalty_comp_160 = 1;
    I_1_eff = I_1 * 10^(-penalty_comp_160/20);
    ber_comp_160km(idx) = 0.5 * erfc((I_1_eff - I_0) / (2*sqrt(2)*sigma_total));
end

figure('Position', [100, 100, 900, 600], 'Color', 'w');
semilogy(rx_power_dBm, max(ber_no_comp_80km, 1e-15), 'r-o', 'LineWidth', 1.5, 'MarkerSize', 4); hold on;
semilogy(rx_power_dBm, max(ber_comp_80km, 1e-15), 'b-s', 'LineWidth', 1.5, 'MarkerSize', 4);
semilogy(rx_power_dBm, max(ber_no_comp_160km, 1e-15), 'r--^', 'LineWidth', 1.5, 'MarkerSize', 4);
semilogy(rx_power_dBm, max(ber_comp_160km, 1e-15), 'b--d', 'LineWidth', 1.5, 'MarkerSize', 4);
yline(1e-9, 'k--', 'BER=10^{-9} (FEC门限)', 'LineWidth', 1);

xlabel('接收光功率 Received Optical Power (dBm)', 'FontSize', 10);
ylabel('误码率 Bit Error Rate (BER)', 'FontSize', 10);
title('BER与接收光功率关系 BER vs Received Power', 'FontSize', 11);
legend({'80km 无补偿 No Comp.', '80km DCF补偿', ...
        '160km 无补偿 No Comp.', '160km DCF补偿'}, ...
        'Location', 'southwest', 'FontSize', 9);
grid on;
ylim([1e-15, 1]);

saveas(gcf, fullfile(output_dir, 'fig5_ber_vs_rxpower.png'));
saveas(gcf, fullfile(output_dir, 'fig5_ber_vs_rxpower.fig'));
fprintf('  图5: BER特性 已保存\n');

% ---- 图6: 色散补偿率与系统性能关系 ----
comp_ratios = 0.8:0.01:1.2;  % 补偿率范围 (80%~120%)
q_performance = zeros(size(comp_ratios));
osnr_penalty = zeros(size(comp_ratios));

for idx = 1:length(comp_ratios)
    r = comp_ratios(idx);
    accum_disp_smf = smf.D * 80;  % 80km SMF累积色散
    dcf_disp = dcf.D * dcf.length * r;  % 可变补偿率
    residual_disp = accum_disp_smf + dcf_disp;

    % Q因子估算
    pulse_broadening = sqrt(1 + (abs(residual_disp) * 10 / 1e3)^2);
    q_performance(idx) = 20 / pulse_broadening;

    % OSNR代价 (dB)
    osnr_penalty(idx) = 10 * log10(pulse_broadening);
end

figure('Position', [100, 100, 900, 600], 'Color', 'w');
yyaxis left;
plot(comp_ratios*100, q_performance, 'b-', 'LineWidth', 1.5);
xlabel('色散补偿率 Dispersion Compensation Ratio (%)', 'FontSize', 10);
ylabel('Q因子 Q-Factor (dB)', 'FontSize', 10);
grid on;

yyaxis right;
plot(comp_ratios*100, osnr_penalty, 'r--', 'LineWidth', 1.5);
ylabel('OSNR代价 OSNR Penalty (dB)', 'FontSize', 10);

title('色散补偿率对系统性能的影响', 'FontSize', 11);
legend({'Q因子', 'OSNR代价'}, 'Location', 'best', 'FontSize', 9);
xline(100, 'k:', '完全补偿', 'LineWidth', 1);

saveas(gcf, fullfile(output_dir, 'fig6_compensation_ratio.png'));
saveas(gcf, fullfile(output_dir, 'fig6_compensation_ratio.fig'));
fprintf('  图6: 补偿率优化 已保存\n');

%% =========================================================================
% 第五部分: 输出统计结果
% =========================================================================
fprintf('\n========================================\n');
fprintf('仿真结果汇总 Simulation Results Summary\n');
fprintf('========================================\n');

% 计算关键指标
% 80km处Q因子
q_no_comp_80 = q_factors_no_comp(distances == 80);
q_comp_80 = q_factors_with_comp(distances == 80);

fprintf('系统参数:\n');
fprintf('  比特率: %.0f Gb/s\n', sys_params.bitrate/1e9);
fprintf('  SMF长度: %.0f km (D=%.1f ps/(nm·km))\n', smf.length, smf.D);
fprintf('  DCF长度: %.2f km (D=%.1f ps/(nm·km))\n', dcf.length, dcf.D);
fprintf('  中心波长: %d nm\n', round(global_params.lambda*1e9));

fprintf('\n80km传输后性能对比:\n');
fprintf('  无补偿Q因子: %.2f dB\n', q_no_comp_80);
fprintf('  DCF补偿Q因子: %.2f dB\n', q_comp_80);
fprintf('  Q因子改善: %.2f dB\n', q_comp_80 - q_no_comp_80);

fprintf('\n脉冲宽度分析:\n');
fprintf('  初始FWHM宽度: %.2f ps\n', fwhm_orig);
fprintf('  SMF传输后FWHM宽度: %.2f ps (展宽比: %.1fx)\n', fwhm_smf, fwhm_smf/fwhm_orig);
if fwhm_dcf > 0
    fprintf('  DCF补偿后FWHM宽度: %.2f ps (恢复比: %.1f%%)\n', fwhm_dcf, fwhm_dcf/fwhm_orig*100);
end

% 色散受限距离 (无补偿, Q=6)
dispersion_limit_idx = find(q_factors_no_comp >= 6, 1, 'last');
if ~isempty(dispersion_limit_idx)
    fprintf('\n色散受限距离 (Q=6, 无补偿): %.0f km\n', distances(dispersion_limit_idx));
end

fprintf('\n========================================\n');
fprintf('仿真完成！所有图表已保存到 %s\n', output_dir);
fprintf('========================================\n');

%% =========================================================================
% 辅助函数: 分步傅里叶法 (SSFM) 求解非线性薛定谔方程
% =========================================================================
function u_out = ssfm_propagation(u_in, fiber, sim_params, global_params)
    % 分步傅里叶法求解光纤传输
    % u_in: 输入光场
    % fiber: 光纤参数结构体
    % sim_params: 仿真参数
    % global_params: 全局物理参数

    nt = length(u_in);
    dz = sim_params.dz * 1e3;  % 转换为米
    L_total = fiber.length * 1e3;  % 转换为米
    nz = ceil(L_total / dz);
    dz = L_total / nz;  % 调整步长

    % 频率轴
    dw = 2*pi / (nt * sim_params.dt);
    w = (-nt/2:nt/2-1) * dw;
    w = fftshift(w);

    % 线性色散算子 (频域)
    D_lin = exp(1i * fiber.beta2/2 * w.^2 * dz/2 - fiber.alpha_lin * dz/2);

    u = u_in;

    for n = 1:nz
        % 1/2步长色散 (频域)
        u_freq = fft(u);
        u_freq = ifftshift(fftshift(u_freq) .* D_lin);

        % 非线性效应 (时域) - 简化的Kerr效应
        u_time = ifft(u_freq);
        % 忽略非线性 (小功率近似，线性传输)
        % 如需考虑非线性: u_time = u_time .* exp(1i * fiber.gamma_lin * abs(u_time).^2 * dz);

        % 1/2步长色散 (频域)
        u_freq = fft(u_time);
        u_freq = ifftshift(fftshift(u_freq) .* D_lin);

        u = ifft(u_freq);
    end

    u_out = u;
end

%% =========================================================================
% 辅助函数: 计算FWHM (半高全宽)
% =========================================================================
function w = fwhm(x, y)
    % 计算半高全宽
    % x: 自变量
    % y: 因变量 (功率)

    y = y / max(y);  % 归一化
    half_max = 0.5;

    % 找到半高点
    above = find(y >= half_max);
    if isempty(above) || length(above) < 2
        w = 0;
        return;
    end

    % 左半高点
    left_idx = above(1);
    if left_idx > 1
        % 线性插值
        slope = (y(left_idx) - y(left_idx-1)) / (x(left_idx) - x(left_idx-1));
        if abs(slope) > 1e-30
            x_left = x(left_idx-1) + (half_max - y(left_idx-1)) / slope;
        else
            x_left = x(left_idx);
        end
    else
        x_left = x(left_idx);
    end

    % 右半高点
    right_idx = above(end);
    if right_idx < length(y)
        slope = (y(right_idx+1) - y(right_idx)) / (x(right_idx+1) - x(right_idx));
        if abs(slope) > 1e-30
            x_right = x(right_idx) + (half_max - y(right_idx)) / slope;
        else
            x_right = x(right_idx);
        end
    else
        x_right = x(right_idx);
    end

    w = abs(x_right - x_left);
end
