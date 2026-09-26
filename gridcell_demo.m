%% gridcell_demo.m  グリッド細胞シミュレーション
% 正方形の箱の中をランダムに走り回る仮想ラットと、1個のグリッド細胞の
% 発火をシミュレーションし、発火率マップに六角格子が現れる様子を
% アニメーションで表示します。
%
% 下の「パラメータ」を変えて遊んでみてください。
%   SPACING : グリッド間隔 [m]（小さくすると格子が細かくなる）
%   ORIENT  : 格子の向き [deg]
%   PHASE   : 格子の位置ずれ [m]
%   SAVE_GIF = true にすると gridcell_demo.gif を保存します。
%
% モデル: 60度ずつ向きの異なる3つの平面波の和で発火率を与え
% (Solstad et al., 2006 Hippocampus)、ポアソン過程でスパイクを生成。
% README の GIF は同じモデルの Python 版 tools/make_gridcell_gif.py で作成。

clear; close all;

%% パラメータ
ARENA     = 1.0;      % 箱の一辺 [m]
T_TOTAL   = 15*60;    % シミュレーション時間 [s]
DT        = 0.02;     % 時間刻み [s]
SPEED     = 0.25;     % 走行速度 [m/s]
TURN_SD   = 0.25;     % 1ステップあたりの向きのゆらぎ [rad]
SPACING   = 0.35;     % グリッド間隔 [m]
ORIENT    = 8;        % 格子の向き [deg]
PHASE     = [0.12 0.07];  % 格子の位置ずれ [m]
RMAX      = 20;       % 最大発火率 [Hz]
NBIN      = 40;       % 発火率マップのビン数（一辺）
SMOOTH_SD = 1.5;      % 平滑化ガウシアンのSD [bin]
N_FRAMES  = 80;       % アニメーションのフレーム数
TAIL      = 20;       % 表示する軌跡の長さ [s]
SAVE_GIF  = false;
rng(1);

%% 軌跡: 壁で反射する相関ランダムウォーク
n   = round(T_TOTAL/DT);
pos = zeros(n, 2);
pos(1,:) = ARENA/2;
hd  = 2*pi*rand;
for i = 2:n
    hd  = hd + TURN_SD*randn;
    nxt = pos(i-1,:) + SPEED*DT*[cos(hd) sin(hd)];
    if nxt(1) <= 0 || nxt(1) >= ARENA, hd = pi - hd; end
    if nxt(2) <= 0 || nxt(2) >= ARENA, hd = -hd;     end
    pos(i,:) = pos(i-1,:) + SPEED*DT*[cos(hd) sin(hd)];
    pos(i,:) = min(max(pos(i,:), 1e-6), ARENA - 1e-6);
end

%% グリッド細胞の発火率とスパイク
k = 4*pi/(sqrt(3)*SPACING);
g = zeros(n, 1);
for j = 0:2
    a = deg2rad(ORIENT) + j*pi/3;
    g = g + cos(k*((pos - PHASE)*[cos(a); sin(a)]));
end
rate   = RMAX*((g + 1.5)/4.5).^3;   % g は [-1.5, 3] -> [0, RMAX]
spikes = rand(n, 1) < rate*DT;

%% 平滑化カーネルとビン番号
r = ceil(3*SMOOTH_SD);
[kx, ky] = meshgrid(-r:r);
kern = exp(-(kx.^2 + ky.^2)/(2*SMOOTH_SD^2));
kern = kern/sum(kern(:));
bin  = min(floor(pos/ARENA*NBIN) + 1, NBIN);   % [x y] のビン番号

%% アニメーション
fig = figure('Color', 'w', 'Position', [100 100 800 430]);
ax1 = subplot(1, 2, 1);
ax2 = subplot(1, 2, 2);
colormap(ax2, jet);
ends = unique(round(n*((1:N_FRAMES)/N_FRAMES).^1.6));
ends = max(ends, round(TAIL/DT));
gifFile = 'gridcell_demo.gif';

for f = 1:numel(ends)
    e  = ends(f);
    s  = max(1, e - round(TAIL/DT));
    sp = find(spikes(1:e));

    % 左: 軌跡とスパイク
    cla(ax1); hold(ax1, 'on');
    plot(ax1, pos(s:e,1), pos(s:e,2), 'Color', [0.6 0.6 0.6], 'LineWidth', 0.8);
    plot(ax1, pos(sp,1), pos(sp,2), '.', 'Color', [0.84 0.15 0.16], 'MarkerSize', 5);
    plot(ax1, pos(e,1), pos(e,2), 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 6);
    hold(ax1, 'off');
    title(ax1, 'Trajectory & spikes');

    % 右: 発火率マップ（平滑化スパイク数 / 平滑化滞在時間）
    occ = accumarray(bin(1:e,[2 1]), 1, [NBIN NBIN]);
    cnt = accumarray(bin(sp,[2 1]), 1, [NBIN NBIN]);
    rm  = conv2(cnt, kern, 'same') ./ max(conv2(occ*DT, kern, 'same'), 1e-12);
    rm(occ == 0) = NaN;
    imagesc(ax2, [0 ARENA], [0 ARENA], rm, 'AlphaData', double(~isnan(rm)));
    set(ax2, 'YDir', 'normal');
    title(ax2, 'Firing rate map');

    for ax = [ax1 ax2]
        axis(ax, 'square');
        set(ax, 'XLim', [0 ARENA], 'YLim', [0 ARENA], 'XTick', [], 'YTick', [], 'Box', 'on');
    end
    sgtitle(fig, sprintf('Grid cell simulation   t = %4.1f min', e*DT/60));
    drawnow;

    if SAVE_GIF
        [A, map] = rgb2ind(frame2im(getframe(fig)), 128);
        delay = 0.08 + 2.9*(f == numel(ends));   % 最終フレームは長めに表示
        if f == 1
            imwrite(A, map, gifFile, 'gif', 'LoopCount', Inf, 'DelayTime', delay);
        else
            imwrite(A, map, gifFile, 'gif', 'WriteMode', 'append', 'DelayTime', delay);
        end
    end
end
