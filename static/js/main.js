(function() {
    var stageWidth = 400;
    // var stageHeight = 700;

    var getUa;
    var viewSelector;
    var sorceObj;
    var httpObjReader;
    var Forms = {};
    var FormsMinitize = {};
    var addProjectButton;
    var workHourPerDay = 3;  // 作業時間／日（以降の計算で使用）

    var touchTimer;
    var eventTarget;

    function init(){
        viewSelector.readDivs();
    }
	
    window.onload = function() {
        // main
        if(getUa() === false){
            init();
        }else{
            // mobile browser / PhoneGap等の処理はコメントアウト
            init();
        }

        httpObjReader = new XMLHttpRequest();
        httpObjReader.open("get", "./php/storage.json");
        httpObjReader.onload = function(){
            sorceObj = JSON.parse(this.responseText);
            // 必要であればプロパティの初期設定など
            displayForms(sorceObj);
        }
        httpObjReader.send(null);
    };

    // viewSelector
    viewSelector = {
        nowSeen : 'viewPROJECT',
        divs: {},
        readDivs: function(){
            this.divs['viewPROJECT'] = document.getElementById('viewProject');
            this.divs['viewTHISMONTH'] = document.getElementById('viewThisMonth');
            this.divs['viewTODAY'] = document.getElementById('viewToday');
            this.divs['viewWORKING'] = document.getElementById('viewWorking');
            this.divs['viewDONE'] = document.getElementById('viewDone');
            this.moveView(this.nowSeen);
        },
        moveView: function(strName){
            var flgErr = true;
            viewSelector.nowSeen = strName;
            for(var n in this.divs){
                if(n == strName){
                    this.divs[n].style.display = 'block';
                    flgErr = false;
                }else{
                    this.divs[n].style.display = 'none';
                }
            }
            if (flgErr) console.log('Err !!!!! at viewSelector.moveView');
        },
        moveRight : function(nowName){
            var flgFind = false;
            for (var n in viewSelector.divs){
                if(flgFind){
                    viewSelector.moveView(n);
                    return;
                }
                if (n == nowName){
                    flgFind = true;
                }
            }
            if (flgFind) viewSelector.moveView('viewPROJECT');
        }
    };

    // getUa
    getUa = function() {
        if ((navigator.userAgent.indexOf('iPhone') > 0 && navigator.userAgent.indexOf('iPad') == -1) || navigator.userAgent.indexOf('iPod') > 0 ) {
            return 'iPhone'; 
        } else if(navigator.userAgent.indexOf('iPad') > 0) {
            return 'iPad';
        } else if(navigator.userAgent.indexOf('Android') > 0) {
            return 'Android';
        } else return false;
    };

    function createDOM(strName, strClass, innerText){
        var elm = document.createElement(strName);
        if(strClass) elm.className = strClass;
        if(innerText) elm.innerHTML = innerText;
        return elm;
    }

    // 計算処理：manhour・deadline
    function calculateMH(){
        for(var n in sorceObj.root){
            if(sorceObj.root[n].parent == "root"){
                calMH(sorceObj.root[n]);
            }
        }
        for(var n in sorceObj.root){
            if(sorceObj.root[n].parent == "root"){
                calDeadline(sorceObj.root[n], sorceObj.root[n].deadline);
            }
        }
    }

	function calDeadline(tgtObj, kizitsu) {
		// 期限が未設定または不正な場合は、対象のタスクの deadline を空にして返す
		if (!kizitsu || isNaN(Date.parse(kizitsu))) {
			tgtObj.deadline = "";
			return "";
		}
		// tgtObj.children が存在しない場合は、元の期限をそのまま返す（本来ここに来ることはないはず）
		if (!tgtObj.children) {
			return kizitsu;
		}
		
		if (tgtObj.children.length === 0) {
        // すでにタスク自身に期日が設定されている場合は、その期日を優先する
        if (tgtObj.deadline && tgtObj.deadline.trim() !== "") {
            return tgtObj.deadline;
        }
        // 期日が設定されていない場合は、作業時間から必要日数を計算して新しい期日を設定する
			var hitsuyouDay = Math.floor(tgtObj.manhour.estimate / workHourPerDay) + 1; // +1 は余裕分
			var mmSec = hitsuyouDay * 86400000;
			var dltime = Date.parse(kizitsu);
			var newKizitsu = dltime - mmSec;
			var nkD = new Date(newKizitsu);
        tgtObj.deadline = String(nkD.getFullYear()) + "-" + String(nkD.getMonth() + 1) + "-" + String(nkD.getDate());
        return tgtObj.deadline;
		} else {
			// 子タスクを逆順に処理
			for (var i = 0; i < tgtObj.children.length; i++) {
				// 最初のループで、親が "root" でない場合は、現在の期限を設定
				if (i === 0 && tgtObj.parent !== "root") {
					tgtObj.deadline = kizitsu;
				}
				// 配列の最後の要素から順に取り出す
				var childId = tgtObj.children[tgtObj.children.length - i - 1];
				var tgt = sorceObj.root[childId];
				// 子タスクが存在しない場合は警告を出してスキップ
				if (!tgt) {
					//console.warn("Undefined child in calDeadline with id:", childId);
					continue;
				}
				kizitsu = calDeadline(tgt, kizitsu);
			}
			return kizitsu;
		}
	}

	function calMH(tgtObj) {
		// tgtObj または children プロパティが存在しない場合は初期値を返す
		if (!tgtObj || !tgtObj.children) {
			return { estimate: 0, actual: 0 };
		}
		
		var sekisanMHestimate = 0;
		var sekisanMHactual = 0;
		
		// 子が無ければ自身の manhour を返す
		if (tgtObj.children.length === 0) {
			return tgtObj.manhour;
		} else {
			var flgAllDone = true;
			// 通常の for ループで子タスクを処理
			for (var i = 0; i < tgtObj.children.length; i++) {
				var childId = tgtObj.children[i];
				var tgt = sorceObj.root[childId];
				// 子タスクが存在しない場合は警告を出してスキップ
				if (!tgt) {
					console.warn("Undefined child with id:", childId);
					console.warn("parent id:", tgtObj);
					continue;
				}
				var b = calMH(tgt);
				sekisanMHestimate += Number(b.estimate);
				sekisanMHactual += Number(b.actual);
				
				if (tgt.done === false) {
					flgAllDone = false;
				}
			}
			tgtObj.manhour.estimate = sekisanMHestimate;
			tgtObj.manhour.actual = sekisanMHactual;
			tgtObj.done = flgAllDone;
			return tgtObj.manhour;
		}
	}

    // ★ 30日以内に期限が設定されている子タスクを持つかチェックする関数
    function hasDeadlineWithin30Days(projectObj) {
        var today = new Date();
        // 30日後の日時を算出
        var thirtyDaysLater = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
        // 再帰的にチェックする関数
        function checkTask(task) {
            if (task.deadline) {
                var d = new Date(task.deadline);
                if (!isNaN(d.getTime())) {
                    // 今日から30日以内に期限がある場合
                    if (d >= today && d <= thirtyDaysLater) {
                        return true;
                    }
                }
            }
            if (task.children && task.children.length > 0) {
                for (var i = 0; i < task.children.length; i++) {
                    var childTask = sorceObj.root[task.children[i]];
                    if (childTask && checkTask(childTask)) {
                        return true;
                    }
                }
            }
            return false;
        }
        return checkTask(projectObj);
    }

    function saveJSON(){
        calculateMH();
        var httpObjSender = new XMLHttpRequest();
        httpObjSender.open("post", "./php/memoSave");
        httpObjSender.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        var str = JSON.stringify(sorceObj, null, 4);
        httpObjSender.send("jsondata=" + encodeURIComponent(str));
    }

    function createEmptyForm(tgtStr){
        var form1 = createDOM("div", "form-container");
        var div = createDOM("div", "form-title");
        var h3 = createDOM("h3", null, tgtStr);
        div.appendChild(h3);
        form1.appendChild(div);
        return form1;
    }

    function createLabel(tgtStr){
        var div = createDOM("div", "form-title");
        var h3 = createDOM("h3", null, tgtStr);
        div.appendChild(h3);
        return div;
    }

    function touchStartFunc(e){
        clearTimeout(touchTimer);
        eventTarget = e;
        touchTimer = setTimeout(renameTitle, 2000);
    }

    function touchStopFunc(){
        eventTarget = null;
        clearTimeout(touchTimer);
    }

    function renameTitle(evt){
        editTitle(eventTarget);
        touchStopFunc();
    }

    function createTitle2(tgtStr){
        var div = createDOM("div", "titleBar-title");
        var h2 = createDOM("h2", null, tgtStr.substring(4, tgtStr.length));
        h2.myTitleName = tgtStr;
        div.appendChild(h2);
        return div;
    }

    function createTitle(tgtStr){
        var div = createDOM("div", "form-title");
        var h2 = createDOM("h2", null, tgtStr);
        h2.addEventListener("dblclick", editTitle, false);
        h2.addEventListener("touchstart", touchStartFunc, false);
        h2.addEventListener("touchend", touchStopFunc, false);
        h2.addEventListener("touchcancel", touchStopFunc, false);
        div.appendChild(h2);
        return div;
    }

    function createSubTitle(tgtStr, intGeneration){
        var div = createDOM("div", "form-title");
        var h3 = createDOM("h3", null, tgtStr);
        var intPad = 20 * intGeneration;
        h3.style.paddingLeft = intPad + "px";
        h3.addEventListener("dblclick", editTitle, false);
        h3.addEventListener("touchstart", touchStartFunc, false);
        h3.addEventListener("touchend", touchStopFunc, false);
        h3.addEventListener("touchcancel", touchStopFunc, false);
        div.appendChild(h3);
        return div;
    }

    function createMemo(tgtObj, strID, flgShow){
        var textArea = createDOM("textarea", "form-field", tgtObj.memo);
        textArea.myName = "detailmemo";
        textArea.myID = strID;
        textArea.onchange = function(e){
            var targetNum = searchMyKey(e.target);
            sorceObj.root[targetNum].memo = e.target.value;
            saveJSON();
        }
        textArea.style.display = flgShow ? "block" : "none";
        return textArea;
    }

    function createMHtimer(strID){
        var div = createDOM("div");
        div.myID = strID;
        
        var btnStart = createDOM("input", "submit-button");
        btnStart.type = "submit";
        btnStart.value = "START";
        btnStart.style.width = "99px";
        btnStart.addEventListener("click", btnPushStart, false);
        
        var btnStop = createDOM("input", "submit-button");
        btnStop.type = "submit";
        btnStop.value = "STOP";
        btnStop.style.width = "99px";
        btnStop.addEventListener("click", btnPushStop, false);
        
        var btnCancel = createDOM("input", "submit-button");
        btnCancel.type = "submit";
        btnCancel.value = "CANCEL";
        btnCancel.style.width = "99px";
        btnCancel.addEventListener("click", btnPushCancel, false);
        
        var btnDone = createDOM("input", "submit-button");
        btnDone.type = "submit";
        btnDone.value = "DONE";
        btnDone.style.width = "99px";
        btnDone.addEventListener("click", btnPushDone, false);
        
        div.appendChild(btnStart);
        div.appendChild(btnStop);
        div.appendChild(btnCancel);
        div.appendChild(btnDone);
        return div;
    }

    function createTime(tgtObj, strID, flgShow){
        var returnDiv = createDOM("div");
        returnDiv.myName = "detailtime";
        returnDiv.myID = strID;
        
        var deadlineSection = createDeadline(tgtObj.deadline, strID);
        var mhSection = createMH(tgtObj, strID);
        var buttons = createMHtimer(strID);

        returnDiv.appendChild(deadlineSection);
        returnDiv.appendChild(mhSection);
        returnDiv.appendChild(buttons);

        returnDiv.style.display = flgShow ? "block" : "none";
        return returnDiv;
    }

    function createCost(tgtObj, strID, flgShow){
        var textArea = createDOM("textarea", "form-field", tgtObj.cost);
        textArea.myName = "detailcost";
        textArea.myID = strID;
        textArea.onchange = function(e){
            var targetNum = searchMyKey(e.target);
            sorceObj.root[targetNum].cost = e.target.value;
            saveJSON();
        }
        textArea.style.display = flgShow ? "block" : "none";
        return textArea;
    }

    function createTool(tgtObj, strID, flgShow){
        var returnDiv = createDOM("div");
        returnDiv.myName = "detailtool";
        returnDiv.myID = strID;

        var buttons = createToolButton(strID);

        returnDiv.appendChild(buttons);
        returnDiv.style.display = flgShow ? "block" : "none";
        return returnDiv;
    }

    function createDeadline(tgtStr, strID){
        var container = createDOM("div");
        var nameDiv = createDOM("span", null, "Deadline");
        var textArea = createDOM("input");
        textArea.type = "date";
        textArea.value = tgtStr;
        textArea.myID = strID;
        textArea.onchange = function(e){
            var targetNum = searchMyKey(e.target);
            sorceObj.root[targetNum].deadline = e.target.value;
            saveJSON();
        }
        container.appendChild(nameDiv);
        container.appendChild(textArea);
        return container;
    }

    function createMH(tgtObj, strID){
        var container = createDOM("div");
        var nameDiv = createDOM("div");
        var nameLabel = createDOM("span", null, "Estimate MH");
        var nameDiv2 = createDOM("div");
        var nameLabel2 = createDOM("span", null, "Actual MH");
        var textArea = createDOM("input");
        var textArea2 = createDOM("input");
        textArea.type = "number";
        textArea2.disabled = "disabled";
        textArea.value = tgtObj.manhour.estimate;
        textArea2.value = tgtObj.manhour.actual;
        textArea.myID = strID;
        textArea.onchange = function(e){
            var targetNum = searchMyKey(e.target);
            sorceObj.root[targetNum].manhour.estimate = e.target.value;
            saveJSON();
        }
        
        nameDiv.appendChild(nameLabel);
        nameDiv.appendChild(textArea);
        nameDiv2.appendChild(nameLabel2);
        nameDiv2.appendChild(textArea2);
        container.appendChild(nameDiv);
        container.appendChild(nameDiv2);
        return container;
    }

    function createProgress(tgtObj, myID){
        var div = createDOM("div");
        
        // remain days 計算
        var today = new Date();
        var dltime = Date.parse(tgtObj.deadline);
        var DLtime = new Date(dltime);
        var remain = DLtime - today;
        var remainDay = Math.floor(remain / 86400000) + 1;
        var h3 = createDOM("h3", null, "あと" + remainDay + "日");
        if(remainDay > 3){
            h3.style.color = "blue";
        } else if(remainDay <= 3 && remainDay > 0){
            h3.style.color = "yellow";
        } else if(remainDay === 0){
            h3.style.color = "red";
        } else{
            h3.style.color = "brack";
        }
        if(tgtObj.done){
            h3.innerHTML = "完了";
            h3.style.color = "black";
        }
        h3.style.float = "right";
        h3.style.paddingRight = "10px";
        
        // progress bar
        var progressBar = createDOM("meter");
        progressBar.id = "progress" + myID;
        progressBar.max = 100;
        
        div.appendChild(progressBar);
        div.appendChild(h3);

        var actVal = Math.round(100 * tgtObj.manhour.actual / tgtObj.manhour.estimate);
        if (actVal > 95) actVal = 95;
        var reqDays = tgtObj.manhour.estimate / workHourPerDay;
        var spentDays = reqDays - remainDay;
        var estVal = Math.round(100 * spentDays / reqDays);
        if (estVal > 100) estVal = 100;
        if (estVal < 1) estVal = 0;

        if(tgtObj.done){
            progressBar.value = 100;
        } else if(remainDay < -1){
            progressBar.value = 100;
            var redVal = actVal;
            var cssRed = "#progress" + myID + "::-webkit-meter-optimum-value {box-shadow: 0px 7px 3px 0px rgba(255,255,255,0.6) inset; background-image: linear-gradient(90deg, #EE82EE " + redVal + "%, #FF0000 " + redVal + "%); background-size: 100% 100%;}";
            var styleRed = document.createElement('style');
            styleRed.appendChild(document.createTextNode(cssRed));
            progressBar.appendChild(styleRed);
        } else if(actVal >= estVal){
            progressBar.value = actVal;
            var blueVal = Math.round(100 * estVal / actVal);
            var cssBlue = "#progress" + myID + "::-webkit-meter-optimum-value {box-shadow: 0px 7px 3px 0px rgba(255,255,255,0.6) inset; background-image: linear-gradient(90deg, #008000 " + blueVal + "%, #0000FF " + blueVal + "%); background-size: 100% 100%;}";
            var styleBlue = document.createElement('style');
            styleBlue.appendChild(document.createTextNode(cssBlue));
            progressBar.appendChild(styleBlue);
        } else if(actVal < estVal){
            progressBar.value = estVal;
            var yellowVal = Math.round(100 * actVal / estVal);
            var cssYellow = "#progress" + myID + "::-webkit-meter-optimum-value {box-shadow: 0px 7px 3px 0px rgba(255,255,255,0.6) inset; background-image: linear-gradient(90deg, #008000 " + yellowVal + "%, #FFFF00 " + yellowVal + "%); background-size: 100% 100%;}";
            var styleYellow = document.createElement('style');
            styleYellow.appendChild(document.createTextNode(cssYellow));
            progressBar.appendChild(styleYellow);
        }
        return div;
    }

    function createRange(tgtStr){
        var elm = createDOM("input");
        elm.type = "range";
        elm.value = tgtStr;
        return elm;
    }

    function createButton(tgtStr){
        var btn = createDOM("input", "submit-button");
        btn.type = "submit";
        btn.value = tgtStr;
        return btn;
    }

    // ボタン処理
    function btnPushStart(e){
        var k = searchMyKey(e.target);
        sorceObj.root[k].start = new Date();
        saveJSON();
    }

    function btnPushCancel(e){
        var k = searchMyKey(e.target);
        sorceObj.root[k].start = "";
        saveJSON();
    }

    function btnPushStop(e){
        var k = searchMyKey(e.target);
        if(sorceObj.root[k].start != ""){
            var nowDate = new Date();
            var mmsec1 = nowDate.getTime();
            var startDate = new Date(Date.parse(sorceObj.root[k].start));
            var mmsec2 = startDate.getTime();
            var hour = Math.round((mmsec1 - mmsec2) / 36000) / 100;
            sorceObj.root[k].manhour.actual = Number(sorceObj.root[k].manhour.actual) + hour;
            sorceObj.root[k].start = "";
            saveJSON();
        }
    }

    function btnPushDone(e){
        btnPushStop(e);
        var k = searchMyKey(e.target);
        sorceObj.root[k].done = true;
        saveJSON();
    }

    function btnPushDelete(e){
        btnPushStop(e);
        var k = searchMyKey(e.target);
        sorceObj.root[k].del = true;
        saveJSON();
    }

    function btnPushHide(e){
        var k = searchMyKey(e.target);
        sorceObj.root[k].shown = false;
        saveJSON();
    }

    // コピー／カット／ペースト機能
    function btnPushCopy(e) {
        var k = searchMyKey(e.target);
        // 対象タスクをディープコピーしてクリップボードに保存
        taskClipboard = JSON.parse(JSON.stringify(sorceObj.root[k]));
        alert("タスクをコピーしました。");
    }

    function btnPushCut(e) {
        var k = searchMyKey(e.target);
        // 対象タスクをクリップボードにコピー
        taskClipboard = JSON.parse(JSON.stringify(sorceObj.root[k]));
        // 親の子リストから削除
        var parentKey = sorceObj.root[k].parent;
        if (parentKey && sorceObj.root[parentKey] && sorceObj.root[parentKey].children) {
            var index = sorceObj.root[parentKey].children.indexOf(Number(k));
            if (index > -1) {
                sorceObj.root[parentKey].children.splice(index, 1);
            }
        }
        // タスクを削除済みフラグに設定し、DOMから除去
        sorceObj.root[k].del = true;
        if (Forms[k]) {
            Forms[k].parentNode.removeChild(Forms[k]);
            delete Forms[k];
        }
        saveJSON();
        alert("タスクをカットしました。");
    }

    function btnPushPaste(e) {
        var tgtKey = searchMyKey(e.target);
        if (taskClipboard == null) {
            alert("ペーストするタスクがありません。");
            return;
        }
        // クリップボードのタスクを新規タスクとして貼り付け
        var newTask = JSON.parse(JSON.stringify(taskClipboard));
        // 新規タスクに対してユニークなIDを付与
        var maxKey = 0;
        for (var key in sorceObj.root) {
            if (maxKey < Number(key)) maxKey = Number(key);
        }
        var newKey = String(maxKey + 1);
        newTask.parent = tgtKey; // 貼り付け先を親に設定
        // ここでは子タスクはコピーしない（必要に応じて再帰的にID割り振りを実装可能）
        newTask.children = [];
        sorceObj.root[newKey] = newTask;
        if (tgtKey != "root" && sorceObj.root[tgtKey]) {
            sorceObj.root[tgtKey].children.push(Number(newKey));
        }
        if (Forms[tgtKey]) {
            createMeAndChild(newKey, sorceObj.root[newKey], Forms[tgtKey], 0, 'viewPROJECT');
        }
        saveJSON();
        alert("タスクをペーストしました。");
    }

    // ツールボタン（DONE, DELETE）
    function createToolButton(strID){
        var div = createDOM("div");
        div.myID = strID;
        
        // DONEボタンを生成（COPY, CUT, PASTEの代わり）
        var btnDone = createDOM("input", "submit-button");
        btnDone.type = "submit";
        btnDone.value = "DONE";
        btnDone.style.width = "149px"; // 必要に応じて幅を調整
        btnDone.addEventListener("click", btnPushDone, false);
        
        var btnDel = createDOM("input", "submit-button");
        btnDel.type = "submit";
        btnDel.value = "DELETE";
        btnDel.style.width = "99px";
        btnDel.addEventListener("click", btnPushDelete, false);

        div.appendChild(btnDone);
        div.appendChild(btnDel);
        return div;
    }

    function createTab(strName, strID){
        var returnObj = createDOM("span", null, " " + strName.toUpperCase() + " ");
        returnObj.myName = strName;
        returnObj.myID = strID;
        returnObj.addEventListener("click", showDetail, false);
        return returnObj;
    }

    function createDetail(tgtObj, strID){
        var div = createDOM("div");
        var tabMemo = createTab("memo", strID);
        var tabTime = createTab("time", strID);
        var tabCost = createTab("cost", strID);
        var tabTool = createTab("tool", strID);
        
        var divMemo = createMemo(tgtObj, strID, true);
        var divTime = createTime(tgtObj, strID, false);
        var divCost = createCost(tgtObj, strID, false);
        var divTool = createTool(tgtObj, strID, false);

        div.appendChild(tabMemo);
        div.appendChild(tabTime);
        div.appendChild(tabCost);
        div.appendChild(tabTool);
        div.appendChild(divMemo);
        div.appendChild(divTime);
        div.appendChild(divCost);
        div.appendChild(divTool);
        
        return div;
    }

    // createSection は「addSection」と「addChild」のみ使用するため、不要な分岐は削除
    function createSection(strKey, tgtObj, strID, intGene){
        var returnObj = false;
        if(strKey == "title"){
            if(sorceObj.root[strID].parent == "root"){
                returnObj = createTitle(tgtObj);
            } else {
                returnObj = createSubTitle(tgtObj, intGene);
            }
            returnObj.myName = strKey;
            returnObj.myID = strID;
            returnObj.addEventListener('click', function(e){switchMinMax(e.target)}, false);
        } else if(strKey == "addChild"){
            returnObj = createEmptyForm(tgtObj);
            returnObj.myName = strKey;
            returnObj.myID = strID;
            returnObj.addEventListener('click', addNewChild, false);
        }
        return returnObj;
    }

    function createTitleBar(tgtDiv, tgtName){
        var titleBar = createDOM("div", "titleBar-container");
        titleBar.myTitleName = tgtName;
        var titleText = createTitle2(tgtName);
        titleText.myTitleName = tgtName;
        titleBar.addEventListener('click', function(e){viewSelector.moveRight(e.target.myTitleName);}, false);
        titleBar.appendChild(titleText);
        tgtDiv.appendChild(titleBar);
    }

    function createForm(strID, tgtObj, intGene) {
        var form1 = createDOM("div", "form-container");
        // 各フォームごとに一意のインスタンスとして保持するため、data属性でIDと状態を設定
        form1.dataset.taskId = strID;
        form1.dataset.minimized = "false"; // 初期状態は展開状態
    
        var titleSection;
        if (sorceObj.root[strID].parent == "root") {
            titleSection = createTitle(tgtObj.title);
        } else {
            titleSection = createSubTitle(tgtObj.title, intGene);
        }
        titleSection.myName = "title";
        // ここで、クリックイベントリスナー内で自分自身（フォーム）を操作する
        titleSection.addEventListener('click', function(e) {
            e.stopPropagation(); // 必要に応じて伝播を止める
            switchMinMax(form1);
        }, false);
        form1.appendChild(titleSection);
    
        var progressSection = createProgress(tgtObj, strID);
        progressSection.myName = "progress";
        form1.appendChild(progressSection);
    
        var detailSection = createDetail(tgtObj, strID);
        detailSection.myName = "detail";
        form1.appendChild(detailSection);
    
        return form1;
    }

    // 新たな引数 filterDone と sortDeadline を追加（未指定なら false とする）
    function createMeAndChild(strID, tgtObj, parentElm, intGene, viewName, filterDone, sortDeadline) {
        filterDone = (typeof filterDone !== 'undefined') ? filterDone : false;
        sortDeadline = (typeof sortDeadline !== 'undefined') ? sortDeadline : false;
    
		try {
			if(tgtObj.del) return;			
		} catch (error) {
			return;
		}
        
        // 期限の計算（必要なら残り日数などの処理）
        var today = new Date();
        var dltime = Date.parse(tgtObj.deadline);
        var DLtime = new Date(dltime);
        var remain = DLtime - today;
        var remainDay = Math.floor(remain / 86400000) + 1;
        if(isNaN(remainDay)){
            remainDay = Number.MAX_VALUE;;
        }
        var formMe;
        // 各ビューごとの表示条件（必要に応じて既存条件を利用）
        if(viewName == 'viewPROJECT' && tgtObj.shown) {
            formMe = createForm(strID, tgtObj, intGene);
        } else if(viewName == 'viewTHISMONTH') {
            formMe = createForm(strID, tgtObj, intGene);
        } else if(viewName == 'viewTODAY' && tgtObj.children.length == 0 && remainDay <= 3 && tgtObj.done == false) {
            formMe = createForm(strID, tgtObj, intGene);
        } else if(viewName == 'viewWORKING' && tgtObj.children.length == 0 && tgtObj.start != '') {
            formMe = createForm(strID, tgtObj, intGene);
        } else if(viewName == 'viewDONE' && tgtObj.children.length == 0 && tgtObj.deadline && remainDay <= 3 && tgtObj.shown && tgtObj.done) {
            formMe = createForm(strID, tgtObj, intGene);
        }

        if(formMe !== undefined){
            if(parentElm != undefined) {
                parentElm.appendChild(formMe);
            } else {
                viewSelector.divs[viewName].appendChild(formMe);
            }
            if(viewName == 'viewDONE') formMe.addEventListener('click', btnPushHide, false);
            var addChild = createSection("addChild", "add child + ", strID, intGene);
            formMe.appendChild(addChild);
        }
        
        // 再帰的に子タスクを処理する部分
        if(filterDone || sortDeadline) {
            // 子タスクの配列をコピー
            var childrenArray = tgtObj.children.slice();
            
            // filterDone が true なら、done が true のタスクを除外
            if(filterDone) {
                childrenArray = childrenArray.filter(function(childId) {
                    var childTask = sorceObj.root[childId];
                    // childTask.done が true の場合のみ除外する（undefinedの場合は false とみなす）
                    if(childTask){
                        return !childTask.done;
                    }else{
                        return false;
                    }

                });
            }
            
            // sortDeadline が true なら、残り期日（deadlineまでの日数）で昇順にソート
            if(sortDeadline) {
                childrenArray.sort(function(a, b) {
                    var childA = sorceObj.root[a];
                    var childB = sorceObj.root[b];
                    
                    var timeA, timeB;
                    
                    // childA が存在し、かつ deadline プロパティが存在し、空文字でないなら Date.parse を実行
                    if(childA && childA.deadline && typeof childA.deadline === "string" && childA.deadline.trim() !== "") {
                        timeA = Date.parse(childA.deadline);
                        if(isNaN(timeA)) {
                            timeA = Number.MAX_VALUE;
                        }
                    } else {
                        timeA = Number.MAX_VALUE;
                    }
                    
                    // childB も同様にチェック
                    if(childB && childB.deadline && typeof childB.deadline === "string" && childB.deadline.trim() !== "") {
                        timeB = Date.parse(childB.deadline);
                        if(isNaN(timeB)) {
                            timeB = Number.MAX_VALUE;
                        }
                    } else {
                        timeB = Number.MAX_VALUE;
                    }
                    
                    var daysA = Math.floor((timeA - Date.now()) / 86400000) + 1;
                    var daysB = Math.floor((timeB - Date.now()) / 86400000) + 1;
                    return daysA - daysB;
                });
            }

            // フィルター／ソート済みの順で再帰呼び出し
            for (var i = 0; i < childrenArray.length; i++) {
                var childId = childrenArray[i];
                createMeAndChild(childId, sorceObj.root[childId], formMe, intGene + 1, viewName, filterDone, sortDeadline);
            }
        } else {
            // 両方 false の場合は通常の順番で処理
            for (var ind in tgtObj.children){
                var keyID = tgtObj.children[ind];
                createMeAndChild(keyID, sorceObj.root[keyID], formMe, intGene + 1, viewName, filterDone, sortDeadline);
            }
        }

        if (formMe !== undefined && viewName != 'viewTODAY' && viewName != 'viewWORKING') minitizeForm(formMe);
        return formMe;
    }

    function createNewProject(e){
        addNewChild({target: {myID: "root"}});
    }

    function addNewChild(e){
        var tgtKey = searchMyKey(e.target);
        var childFormat = {
            "title": '新しいタスク',
            "progress": null,
            "deadline": '',
            "manhour": {
                "estimate": 1,
                "actual": 0
            },
            "memo": "",
            "cost": "",
            "start": "",
            "done": false,
            "parent": tgtKey,  // 親IDを正しく設定
            "children": [],
            "shown": true,
            "del": false
        };
        var maxKey = 0;
        for (var key in sorceObj.root) {
            if(maxKey < Number(key)) maxKey = Number(key);
        }
        var newKey = String(maxKey + 1);
        sorceObj.root[newKey] = childFormat;
        if(tgtKey != "root") sorceObj.root[tgtKey].children.push(Number(newKey));
        if(Forms[tgtKey]) {
            createMeAndChild(newKey, sorceObj.root[newKey], Forms[tgtKey], 0, 'viewPROJECT');
        }
        saveJSON();
    }

    // フォームの最小化／展開
    function searchMyKey(tgtElm){
        for(var i = 0; i < 10; i++){
            if(tgtElm.myID !== undefined){
                return tgtElm.myID;
            } else {
                tgtElm = tgtElm.parentNode;
            }
        }
        return false;
    }
    function minitizeForm(tgtForm) {
        var ch = tgtForm.childNodes;
        for (var i = 0; i < ch.length; i++) {
            // タイトルと進捗部分は常に表示、それ以外を隠す
            if (ch[i].myName !== "title" && ch[i].myName !== "progress") {
                ch[i].style.display = "none";
            }
        }
    }
    function showAllForm(tgtForm) {
        var ch = tgtForm.childNodes;
        for (var i = 0; i < ch.length; i++) {
            ch[i].style.display = "block";
        }
    }
    function switchMinMax(formElm) {
        if (formElm.dataset.minimized === "true") {
            showAllForm(formElm);
            formElm.dataset.minimized = "false";
        } else {
            minitizeForm(formElm);
            formElm.dataset.minimized = "true";
        }
    }
    function showDetail(e){
        var tgtID = searchMyKey(e.target);
        var strTab = e.target.myName;
        if(!FormsMinitize[tgtID]){
            var pNode = e.target.parentNode;
            var ch = pNode.childNodes;
            for (var i = 0; i < ch.length; i++) {
                if(ch[i].myName && ch[i].myName.indexOf("detail") !== -1){
                    ch[i].style.display = (ch[i].myName == "detail" + strTab) ? "block" : "none";
                }
            }
        }
    }

    // タイトル編集
    function inputString(defaultStr){
        var returnStr = window.prompt("タイトルを入力してください", defaultStr);
        if(returnStr != "" && returnStr != null){
            return returnStr;
        } else {
            return false;
        }
    }
    function editTitle(e){
        var tgtElm = e.target;
        var tgtKey = searchMyKey(tgtElm);
        var tgtObj = sorceObj.root[tgtKey];
        var nowTitle = tgtObj.title;
        var strNewTitle = inputString(nowTitle);
        if(strNewTitle !== false){
            tgtObj.title = strNewTitle;
            tgtElm.innerHTML = strNewTitle;
            saveJSON();
        }
    }

// 補助関数：期日までの残り日数を計算（未設定は Infinity とする）
function computeRemainingDays(task) {
    var today = new Date();
    var dltime = Date.parse(task.deadline);
    var DLtime = new Date(dltime);
    var remain = DLtime - today;
    var remainDay = Math.floor(remain / 86400000) + 1;
    if (isNaN(remainDay)) {
        remainDay = Infinity;
    }
    return remainDay;
}

// 補助関数：そのタスク（またはその子孫）に、Today 表示対象となる末端タスクがあるかをチェック
function isEligibleForToday(task) {
    if (!task.children || task.children.length === 0) {
        // 末端タスク：残り日数が 3 日以下かつ未完了なら表示対象
        return computeRemainingDays(task) <= 3 && task.done === false;
    } else {
        // 子タスクがある場合、いずれかの子が対象ならこのタスクも対象とする
        for (var i = 0; i < task.children.length; i++){
            var child = sorceObj.root[task.children[i]];
            if (child && isEligibleForToday(child)) {
                return true;
            }
        }
        return false;
    }
}

function displayForms(tgtData) {
    // 各 view 用のタイトルバーを生成
    for (var n in viewSelector.divs) {
        createTitleBar(viewSelector.divs[n], n);
    }
    
    var intGenerationStart = 0;
    
    // ルート直下（プロジェクトレベル）のタスクを配列にまとめる
    var rootTasks = [];
    for (var n in tgtData.root) {
        if (tgtData.root[n].parent == "root") {
            rootTasks.push({ id: n, task: tgtData.root[n], remainingDays: computeRemainingDays(tgtData.root[n]) });
        }
    }
    
    // (1) viewPROJECT：すべてのプロジェクトを残り日数昇順で表示
    var projectTasks = rootTasks.slice();
    projectTasks.sort(function(a, b) {
        return a.remainingDays - b.remainingDays;
    });
    for (var i = 0; i < projectTasks.length; i++) {
        createMeAndChild(projectTasks[i].id, projectTasks[i].task, viewSelector.divs['viewPROJECT'], intGenerationStart, 'viewPROJECT', false, true);
    }
    
    // (2) viewTHISMONTH：子タスクの中に「30日以内に期限」があるプロジェクトのみ表示
    var thisMonthTasks = [];
    for (var i = 0; i < rootTasks.length; i++) {
        if (hasDeadlineWithin30Days(rootTasks[i].task)) {
            thisMonthTasks.push(rootTasks[i]);
        }
    }
    thisMonthTasks.sort(function(a, b) {
        return a.remainingDays - b.remainingDays;
    });
    for (var i = 0; i < thisMonthTasks.length; i++) {
        createMeAndChild(thisMonthTasks[i].id, thisMonthTasks[i].task, viewSelector.divs['viewTHISMONTH'], intGenerationStart, 'viewTHISMONTH', true, true);
    }

    // (3) viewTODAY：親タスクも昇順で、かつプロジェクト内に対象の末端タスクがあるものだけ表示
    var todayTasks = [];
    for (var i = 0; i < rootTasks.length; i++) {
        if (isEligibleForToday(rootTasks[i].task)) {
            todayTasks.push(rootTasks[i]);
        }
    }
    todayTasks.sort(function(a, b) {
        return a.remainingDays - b.remainingDays;
    });
    for (var i = 0; i < todayTasks.length; i++) {
        // createMeAndChild 内では、viewNameが"viewTODAY"の場合、親タスク（子を持つもの）は最小化状態（タイトルのみ表示）にするよう実装する
        createMeAndChild(todayTasks[i].id, todayTasks[i].task, viewSelector.divs['viewTODAY'], intGenerationStart, 'viewTODAY', true, true);
    }
    
    // (4) viewWORKING：ルートタスクを表示（ここは必要に応じてソートも可能）
    var workingTasks = rootTasks.slice();
    workingTasks.sort(function(a, b) {
        return a.remainingDays - b.remainingDays;
    });
    for (var i = 0; i < workingTasks.length; i++) {
        createMeAndChild(workingTasks[i].id, workingTasks[i].task, viewSelector.divs['viewWORKING'], intGenerationStart, 'viewWORKING');
    }
    
    // (5) viewDONE：ルートタスクを表示（こちらも昇順にソート）
    var doneTasks = rootTasks.slice();
    doneTasks.sort(function(a, b) {
        return a.remainingDays - b.remainingDays;
    });
    for (var i = 0; i < doneTasks.length; i++) {
        createMeAndChild(doneTasks[i].id, doneTasks[i].task, viewSelector.divs['viewDONE'], intGenerationStart, 'viewDONE');
    }
    
    // 新規プロジェクト（またはタスク）追加ボタンの生成
    addProjectButton = createButton("add + ");
    addProjectButton.addEventListener("click", function(e) {
        createNewProject(e);
        setTimeout(function(){ 
            location.reload(); 
        }, 200);
    }, false);
    viewSelector.divs['viewPROJECT'].appendChild(addProjectButton);
}

})();
