class Initialize_parameters:

  def __init__(self):
        pass

  def kappa_sigma_theta_initial_estimators(self,dt,cond_vol):
    DF=pd.DataFrame(cond_vol)
    dif=(DF.diff()).dropna()
    rs=DF.iloc[:-1]
    Y=(dif/np.sqrt(rs)).dropna()
    Y.columns=['Y']
    B1=dt/np.sqrt(rs)
    B1.columns=['Beta1']
    B2=dt*np.sqrt(rs)
    B2.columns=['Beta2']
    X=(B1.join(B2)).dropna()
    X=X.iloc[:-1]
    X.index=Y.index
    modl=sm.OLS(Y,X)
    resl=modl.fit()
    kappa=-resl.params[-1]
    theta=resl.params[0]/kappa
    xi=np.std(resl.resid)/np.sqrt(dt)
    return  kappa,theta,xi

  @staticmethod
  @jit(nopython=True)
  def MCS(v0, kappa, theta, xi, n, dt, W_v, W_S):
    vs    = np.zeros(n)
    vs[0] = v0
    Sl    = np.zeros(n)
    Sl[0] = 0
    for t in range(1,n):
        #stochastic_term=(((1/2)*(xi**2)*(kappa**-1)*(1-np.exp(-2*kappa*dt))*vt[t-1])**(1/2))*np.random.normal(0,1) #np.random.normal(0,(vt[t-1]*(1-np.exp(-kappa*dt))*(1/2)*(xi**2)/kappa)**(1/2)) *vt[t-1]
        vs[t] = np.maximum(vs[t-1]+kappa*(theta-vs[t-1])*dt+xi*np.sqrt(vs[t-1])*W_v[t]*np.sqrt(dt),0.00001) #(np.exp(-kappa*dt)*vt[t-1] + theta*(1-np.exp(-kappa*dt)) + stochastic_term)
        Sl[t] = (r - 0.5*vs[t])*dt + np.sqrt((1-(rho)**2)*vs[t]*dt)*W_S[t]+rho*np.sqrt(dt*vs[t])*W_v[t]
    return vs,Sl

  def HeMC (self,v0, kappa, theta, xi, n, dt,W_v,W_S):

    # Generate paths
    MC=self.MCS(v0, kappa, theta, xi, n, dt,W_v,W_S)
    vt=MC[0]
    St=MC[1]

    B1=(((vt[1:].sum())*(vt[:-1]**-1).sum())-n*(vt[1:]*(vt[:-1]**-1)).sum())/(((vt[:-1].sum())*(vt[:-1]**-1).sum())-n**2)
    kappa=-(1/dt)*np.log(B1)
    B2=(((vt[1:]*vt[:-1]**-1).sum())-n*B1)/((1-B1)*(vt[:-1]**-1).sum())
    theta=B2
    B3=(((vt[1:]-(vt[:-1])*B1-B2*(1-B1))**2)*(n*vt[:-1])**-1).sum()
    xi=(2*kappa*B3)/(1-B1**2)

    def solver(p):
        corr_calculus=(1/2)*(np.log(1-p**2)+np.log(vt[:-1])+np.log(dt))
        m=1/2*(((1-p**2)*vt[:-1]*dt)**-1)*(St[:-1]+(r-(1/2)*vt[:-1]-(p/xi)*kappa*(theta-vt[:-1]))*dt+(p/xi)*(vt[:-1]-vt[1:]))**2
        MLE=(corr_calculus*m).sum()
        return -MLE

    x0 = rho
    bnds=((-1,0),)
    res = minimize(solver,x0,method='SLSQP',options={'disp':False,'maxiter':2000},bounds=bnds)
    p=res.x

    return kappa,theta,xi,p
